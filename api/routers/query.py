"""Unified query endpoint with intelligent routing."""

import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from neo4j.exceptions import ServiceUnavailable

from api.models.query import (
    ExtractedEntities,
    Intent,
    QueryReasoningBlock,
    QueryRequest,
    QueryResponse,
    QueryResult,
    QueryType,
    RoutingDecision,
    TimingInfo,
)
from api.services.fusion import (
    normalize_graph_results,
    normalize_vector_results,
    reciprocal_rank_fusion,
)
from api.services.graph_templates import TEMPLATES, get_template
from api.services.neo4j_service import Neo4jService, get_neo4j_service
from api.services.query_router import QueryRouter, get_query_router
from api.services.reranker import apply_topic_relevance_boost, rerank_results

router = APIRouter(prefix="/api/v1", tags=["query"])


def _select_graph_template(decision: RoutingDecision) -> str | None:
    """Select the best graph template based on routing decision."""
    # If router suggested a template, validate it exists
    if decision.template_hint and decision.template_hint in TEMPLATES:
        return decision.template_hint

    # Otherwise, infer from entities and intent
    entities = decision.entities

    # If specific rec_ids mentioned, use those
    if entities.rec_ids:
        return "recommendation_with_evidence"

    # If topics mentioned, filter by topic
    if entities.topics:
        return "recommendations_by_topic"

    # For evidence lookups, use the full chain
    if decision.intent == Intent.EVIDENCE_LOOKUP:
        return "evidence_chain_full"

    # Default to topic-based if we have conditions (map to topics)
    if entities.conditions:
        return "recommendations_by_topic"

    return None


def _build_graph_params(decision: RoutingDecision, template_name: str) -> dict:
    """Build parameters for the selected graph template."""
    entities = decision.entities
    template = get_template(template_name)

    if template is None:
        return {}

    params = {}

    # Map entities to template parameters
    if template_name == "recommendation_only":
        params["rec_ids"] = entities.rec_ids or ["REC_001"]

    elif template_name == "recommendation_with_evidence":
        params["rec_ids"] = entities.rec_ids or ["REC_001"]

    elif template_name == "evidence_chain_full":
        params["rec_ids"] = entities.rec_ids or ["REC_001"]

    elif template_name == "studies_for_recommendation":
        params["rec_id"] = entities.rec_ids[0] if entities.rec_ids else "REC_001"

    elif template_name == "recommendations_by_topic":
        # Map conditions to topics
        if entities.topics:
            params["topic"] = entities.topics[0]
        elif entities.conditions:
            # Try to map condition to a topic
            condition_topic_map = {
                "kidney": "Pharmacotherapy",
                "ckd": "Pharmacotherapy",
                "renal": "Pharmacotherapy",
                "heart": "Pharmacotherapy",
                "cardiovascular": "Pharmacotherapy",
                "ascvd": "Pharmacotherapy",
                "blood sugar": "Glycemic Control",
                "glucose": "Glycemic Control",
                "hba1c": "Glycemic Control",
                "a1c": "Glycemic Control",
                "prediabetes": "Prediabetes",
                "prevention": "Prediabetes",
            }
            for condition in entities.conditions:
                condition_lower = condition.lower()
                for keyword, topic in condition_topic_map.items():
                    if keyword in condition_lower:
                        params["topic"] = topic
                        break
                if "topic" in params:
                    break
            if "topic" not in params:
                params["topic"] = "Pharmacotherapy"  # Default
        else:
            params["topic"] = "Pharmacotherapy"

    return params


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Unified query with intelligent routing",
    description="Analyzes the question and automatically selects the best retrieval strategy (vector, graph, or hybrid)",
    responses={
        200: {"description": "Successful query with ranked results"},
        422: {"description": "Invalid request"},
        503: {"description": "Database or LLM service unavailable"},
    },
)
async def unified_query(
    request: QueryRequest,
    neo4j: Annotated[Neo4jService, Depends(get_neo4j_service)],
    query_router: Annotated[QueryRouter, Depends(get_query_router)],
) -> QueryResponse:
    """
    Process a natural language question with intelligent query routing.

    The system analyzes the question and automatically selects the best retrieval strategy:

    - **VECTOR**: Semantic similarity search for open-ended questions
    - **GRAPH**: Structural traversal for specific lookups and citation chains
    - **HYBRID**: Combined approach for patient-specific questions with multiple factors

    Results are fused using Reciprocal Rank Fusion (RRF) and re-ranked based on
    clinical relevance (recommendation strength, evidence quality).
    """
    start_time = time.perf_counter()
    timing = {}

    # Step 1: Route the query
    try:
        decision, routing_ms = query_router.route(request.question)
        timing["routing_ms"] = routing_ms
    except Exception as e:
        # Fallback to vector search if routing fails
        decision = RoutingDecision(
            query_type=QueryType.VECTOR,
            intent=Intent.GENERAL_QUESTION,
            confidence=0.5,
            entities=ExtractedEntities(),
            template_hint=None,
            reasoning=f"Routing failed: {e}",
        )
        timing["routing_ms"] = 0

    # Step 2: Execute retrieval based on routing decision
    vector_results = []
    graph_results = []
    template_used = None
    paths_used = []

    try:
        if decision.query_type in (QueryType.VECTOR, QueryType.HYBRID):
            # Execute vector search
            records, embedding_ms, search_ms = neo4j.vector_search_with_embedding(
                query_text=request.question,
                node_type="Recommendation",
                top_k=request.top_k,
            )
            vector_results = normalize_vector_results(records)
            timing["embedding_ms"] = embedding_ms
            timing["vector_search_ms"] = search_ms
            paths_used.append("vector")

        if decision.query_type in (QueryType.GRAPH, QueryType.HYBRID):
            # Select and execute graph template
            template_used = _select_graph_template(decision)
            if template_used:
                template = get_template(template_used)
                if template:
                    params = _build_graph_params(decision, template_used)
                    records, graph_ms = neo4j.execute_graph_query(
                        cypher=template.cypher,
                        params=params,
                    )
                    graph_results = normalize_graph_results(records)
                    timing["graph_search_ms"] = graph_ms
                    paths_used.append("graph")

    except ServiceUnavailable:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable. Please try again later.",
        ) from None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Query execution failed: {e}",
        ) from None

    # Step 3: Fuse results if hybrid
    fusion_start = time.perf_counter()
    if decision.query_type == QueryType.HYBRID and vector_results and graph_results:
        fused_results = reciprocal_rank_fusion([vector_results, graph_results])
        timing["fusion_ms"] = int((time.perf_counter() - fusion_start) * 1000)
    elif vector_results:
        fused_results = vector_results
        for r in fused_results:
            r["source"] = "vector"
    elif graph_results:
        fused_results = graph_results
        for r in fused_results:
            r["source"] = "graph"
    else:
        fused_results = []

    # Step 4: Re-rank results
    rerank_start = time.perf_counter()
    reranked_results = rerank_results(fused_results)

    # Apply topic relevance boost if topics were extracted
    if decision.entities.topics:
        reranked_results = apply_topic_relevance_boost(
            reranked_results,
            decision.entities.topics,
        )

    timing["rerank_ms"] = int((time.perf_counter() - rerank_start) * 1000)

    # Step 5: Build response
    total_ms = int((time.perf_counter() - start_time) * 1000)
    timing["total_ms"] = total_ms

    # Convert to QueryResult models
    results = []
    for item in reranked_results[: request.top_k]:
        results.append(
            QueryResult(
                rec_id=item.get("rec_id", ""),
                rec_text=item.get("rec_text", ""),
                strength=item.get("strength"),
                direction=item.get("direction"),
                topic=item.get("topic"),
                score=item.get("score", 0.0),
                evidence_quality=item.get("evidence_quality"),
                study_count=item.get("study_count"),
                source=item.get("source", "vector"),
            )
        )

    # Build reasoning block
    reasoning = QueryReasoningBlock(
        routing=decision,
        paths_used=paths_used,
        template_used=template_used,
        vector_candidates=len(vector_results) if vector_results else None,
        graph_candidates=len(graph_results) if graph_results else None,
        fusion_method="RRF" if decision.query_type == QueryType.HYBRID else None,
        rerank_applied=True,
        timing=TimingInfo(
            routing_ms=timing.get("routing_ms", 0),
            embedding_ms=timing.get("embedding_ms"),
            vector_search_ms=timing.get("vector_search_ms"),
            graph_search_ms=timing.get("graph_search_ms"),
            fusion_ms=timing.get("fusion_ms"),
            rerank_ms=timing.get("rerank_ms"),
            total_ms=timing["total_ms"],
        ),
    )

    return QueryResponse(results=results, reasoning=reasoning)
