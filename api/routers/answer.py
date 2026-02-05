"""Answer generation endpoint with LLM synthesis."""

import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from neo4j.exceptions import ServiceUnavailable

from api.models.answer import (
    AnswerReasoning,
    AnswerRequest,
    AnswerResponse,
    Citation,
    ContextUsage,
    StudyCitation,
)
from api.models.query import ExtractedEntities, Intent, QueryType
from api.services.answer_generator import AnswerGenerator, get_answer_generator
from api.services.fusion import (
    normalize_graph_results,
    normalize_vector_results,
    reciprocal_rank_fusion,
)
from api.services.graph_templates import get_template
from api.services.neo4j_service import Neo4jService, get_neo4j_service
from api.services.query_router import QueryRouter, get_query_router
from api.services.reranker import rerank_results

router = APIRouter(prefix="/api/v1", tags=["answer"])


@router.post(
    "/answer",
    response_model=AnswerResponse,
    summary="Generate natural language answer with citations",
    description="Retrieves relevant recommendations and generates a conversational answer with proper citations",
    responses={
        200: {"description": "Successful answer generation"},
        422: {"description": "Invalid request"},
        503: {"description": "Database or LLM service unavailable"},
    },
)
async def generate_answer(
    request: AnswerRequest,
    neo4j: Annotated[Neo4jService, Depends(get_neo4j_service)],
    query_router: Annotated[QueryRouter, Depends(get_query_router)],
    answer_generator: Annotated[AnswerGenerator, Depends(get_answer_generator)],
) -> AnswerResponse:
    """
    Generate a natural language answer from the clinical guideline knowledge base.

    The system:
    1. Routes the question to determine retrieval strategy
    2. Retrieves relevant recommendations via vector/graph/hybrid search
    3. Generates a conversational answer using Claude Sonnet
    4. Returns the answer with citations to specific recommendations

    Answers always cite specific recommendation IDs and include strength/direction context.
    """
    start_time = time.perf_counter()

    # Step 1: Route the query to determine retrieval strategy
    try:
        routing_decision, routing_time = query_router.route(request.question)
    except Exception:
        # Default to vector search if routing fails
        from api.models.query import RoutingDecision
        routing_decision = RoutingDecision(
            query_type=QueryType.VECTOR,
            intent=Intent.GENERAL_QUESTION,
            confidence=0.5,
            entities=ExtractedEntities(),
            template_hint=None,
            reasoning="Routing failed, defaulting to vector search",
        )

    # Step 2: Retrieve recommendations
    vector_results = []
    graph_results = []

    try:
        # Always do vector search for answer generation
        records, _, _ = neo4j.vector_search_with_embedding(
            query_text=request.question,
            node_type="Recommendation",
            top_k=request.top_k,
        )
        vector_results = normalize_vector_results(records)

        # If hybrid or graph, also do graph search
        if routing_decision.query_type in (QueryType.GRAPH, QueryType.HYBRID):
            template_name = _select_template(routing_decision)
            if template_name:
                template = get_template(template_name)
                if template:
                    params = _build_params(routing_decision, template_name)
                    graph_records, _ = neo4j.execute_graph_query(
                        cypher=template.cypher,
                        params=params,
                    )
                    graph_results = normalize_graph_results(graph_records)

    except ServiceUnavailable:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable. Please try again later.",
        ) from None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Retrieval failed: {e}",
        ) from None

    # Step 3: Fuse and rerank results
    if vector_results and graph_results:
        fused = reciprocal_rank_fusion([vector_results, graph_results])
    elif vector_results:
        fused = vector_results
    elif graph_results:
        fused = graph_results
    else:
        fused = []

    reranked = rerank_results(fused) if fused else []
    results_retrieved = len(reranked)

    # Limit to top_k for answer generation
    top_results = reranked[:request.top_k]

    # Step 4: Generate answer with conversation context
    # Convert conversation history to dict format for generator
    history = None
    if request.conversation_history:
        history = [{"role": t.role, "content": t.content} for t in request.conversation_history]

    answer_text, tokens, gen_time, context_usage_dict = answer_generator.generate(
        question=request.question,
        recommendations=top_results,
        include_studies=request.include_studies,
        conversation_history=history,
    )

    # Step 5: Build citations
    citations = []
    if request.include_citations:
        for rec in top_results:
            citations.append(Citation(
                rec_id=rec.get("rec_id", ""),
                rec_text=rec.get("rec_text", ""),
                strength=rec.get("strength"),
                direction=rec.get("direction"),
                topic=rec.get("topic"),
            ))

    # Step 6: Fetch studies if requested
    studies_cited = []
    if request.include_studies and top_results:
        studies_cited = await _fetch_studies(neo4j, top_results)

    total_time = int((time.perf_counter() - start_time) * 1000)

    # Build context usage from generator response
    context_usage = ContextUsage(
        history_turns_received=context_usage_dict.get("history_turns_received", 0),
        history_turns_used=context_usage_dict.get("history_turns_used", 0),
        history_summarized=context_usage_dict.get("history_summarized", False),
        estimated_context_tokens=context_usage_dict.get("estimated_context_tokens", 0),
    )

    reasoning = AnswerReasoning(
        query_routing=routing_decision.query_type.value,
        results_retrieved=results_retrieved,
        results_used=len(top_results),
        generation_time_ms=gen_time,
        total_time_ms=total_time,
        model_used=answer_generator.model,
        tokens_used=tokens,
        context_usage=context_usage,
    )

    return AnswerResponse(
        answer=answer_text,
        citations=citations,
        studies_cited=studies_cited,
        reasoning=reasoning,
    )


def _select_template(decision) -> str | None:
    """Select graph template based on routing decision."""
    # Explicit hint takes priority
    if decision.template_hint:
        return decision.template_hint

    entities = decision.entities

    # V2 templates for conditions and medications
    if entities.conditions:
        return "recommendations_by_condition"
    if entities.medications:
        return "recommendations_by_intervention"

    # V1 templates
    if entities.topics:
        return "recommendations_by_topic"
    if entities.rec_ids:
        return "recommendation_with_evidence"

    # Fallback: if GRAPH routing but no entities, try conditions overview
    if decision.query_type == QueryType.GRAPH:
        return "conditions_overview"

    return None


def _build_params(decision, template_name: str) -> dict:
    """Build parameters for graph template."""
    entities = decision.entities

    # V2 templates for conditions and interventions
    if template_name == "recommendations_by_condition":
        if entities.conditions:
            return {"condition_name": entities.conditions[0]}
        return {"condition_name": "Diabetic Kidney Disease"}

    if template_name == "recommendations_by_intervention":
        if entities.medications:
            return {"intervention_name": entities.medications[0]}
        return {"intervention_name": "SGLT2 Inhibitors"}

    if template_name == "recommendations_by_care_phase":
        # Extract care phase from topics (Haiku puts care phases there)
        care_phase_keywords = ["screening", "prevention", "diagnosis", "treatment", "follow-up", "complication", "comorbidity"]
        if entities.topics:
            for topic in entities.topics:
                topic_lower = topic.lower()
                for keyword in care_phase_keywords:
                    if keyword in topic_lower:
                        return {"phase_name": topic}
        return {"phase_name": "Treatment"}

    # Overview templates don't need params
    if template_name in ("conditions_overview", "interventions_overview", "care_phases_overview"):
        return {}

    # V1 templates
    if template_name == "recommendations_by_topic":
        if entities.topics:
            return {"topic": entities.topics[0]}
        return {"topic": "Pharmacotherapy"}

    if template_name in ("recommendation_only", "recommendation_with_evidence", "evidence_chain_full"):
        if entities.rec_ids:
            return {"rec_ids": entities.rec_ids}
        return {"rec_ids": ["REC_001"]}

    if template_name == "studies_for_recommendation":
        if entities.rec_ids:
            return {"rec_id": entities.rec_ids[0]}
        return {"rec_id": "REC_001"}

    return {}


async def _fetch_studies(neo4j: Neo4jService, recommendations: list[dict]) -> list[StudyCitation]:
    """Fetch supporting studies for the top recommendations."""
    studies = []
    seen_pmids = set()

    # Get rec_ids from top 3 recommendations
    rec_ids = [r.get("rec_id") for r in recommendations[:3] if r.get("rec_id")]

    if not rec_ids:
        return studies

    # Query for studies
    template = get_template("evidence_chain_full")
    if template:
        try:
            records, _ = neo4j.execute_graph_query(
                cypher=template.cypher,
                params={"rec_ids": rec_ids},
            )

            for record in records:
                studies_list = record.get("studies", [])
                if isinstance(studies_list, list):
                    for study in studies_list[:5]:  # Limit studies per rec
                        if study and isinstance(study, dict):
                            pmid = study.get("pmid")
                            if pmid and pmid not in seen_pmids:
                                seen_pmids.add(pmid)
                                studies.append(StudyCitation(
                                    pmid=pmid,
                                    title=study.get("title", "Unknown"),
                                    journal=study.get("journal"),
                                    year=study.get("year"),
                                ))
        except Exception:
            pass  # Studies are optional, don't fail the request

    return studies[:10]  # Limit total studies
