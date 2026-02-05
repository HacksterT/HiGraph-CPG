"""Search endpoints for vector and graph queries."""

import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from neo4j.exceptions import ServiceUnavailable

from api.models.search import (
    ClinicalModuleResult,
    EvidenceBodyResult,
    GraphReasoningBlock,
    GraphSearchRequest,
    GraphSearchResponse,
    KeyQuestionResult,
    NodeType,
    ReasoningBlock,
    RecommendationResult,
    StudyResult,
    TemplateInfo,
    VectorSearchRequest,
    VectorSearchResponse,
)
from api.services.graph_templates import (
    TEMPLATES,
    get_template,
    list_templates,
    validate_params,
)
from api.services.neo4j_service import Neo4jService, get_neo4j_service

router = APIRouter(prefix="/api/v1/search", tags=["search"])


def _build_result(node_type: NodeType, record: dict):
    """Build the appropriate result model based on node type."""
    score = round(record["similarity_score"], 4)

    if node_type == NodeType.RECOMMENDATION:
        return RecommendationResult(
            rec_id=record["rec_id"],
            rec_text=record["rec_text"],
            strength=record.get("strength"),
            direction=record.get("direction"),
            topic=record.get("topic"),
            similarity_score=score,
        )
    elif node_type == NodeType.STUDY:
        return StudyResult(
            study_id=record["study_id"],
            title=record["title"] or "Unknown",
            abstract=record.get("abstract"),
            authors=record.get("authors"),
            journal=record.get("journal"),
            year=record.get("year"),
            pmid=record.get("pmid"),
            study_type=record.get("study_type"),
            similarity_score=score,
        )
    elif node_type == NodeType.KEY_QUESTION:
        return KeyQuestionResult(
            kq_id=record["kq_id"],
            question_text=record["question_text"],
            kq_number=record.get("kq_number"),
            population=record.get("population"),
            intervention=record.get("intervention"),
            similarity_score=score,
        )
    elif node_type == NodeType.EVIDENCE_BODY:
        return EvidenceBodyResult(
            evidence_id=record["evidence_id"],
            key_findings=record["key_findings"] or "No findings recorded",
            quality_rating=record.get("quality_rating"),
            num_studies=record.get("num_studies"),
            similarity_score=score,
        )
    elif node_type == NodeType.CLINICAL_MODULE:
        return ClinicalModuleResult(
            module_id=record["module_id"],
            module_name=record["module_name"],
            description=record.get("description"),
            topics=record.get("topics"),
            similarity_score=score,
        )
    else:
        raise ValueError(f"Unknown node type: {node_type}")


@router.post(
    "/vector",
    response_model=VectorSearchResponse,
    summary="Vector similarity search",
    description="Search for semantically similar nodes using vector embeddings. Supports Recommendation, Study, KeyQuestion, EvidenceBody, and ClinicalModule node types.",
    responses={
        200: {"description": "Successful search with ranked results"},
        422: {"description": "Invalid request parameters"},
        503: {"description": "Database unavailable"},
    },
)
async def vector_search(
    request: VectorSearchRequest,
    neo4j: Annotated[Neo4jService, Depends(get_neo4j_service)],
) -> VectorSearchResponse:
    """
    Perform vector similarity search against the knowledge graph.

    The query text is embedded using OpenAI's text-embedding-3-small model
    and matched against the appropriate vector index in Neo4j based on node_type.

    Supported node types:
    - **Recommendation**: Clinical recommendations with strength and direction
    - **Study**: Research studies with abstracts, journals, and PMIDs
    - **KeyQuestion**: Key questions from the guideline methodology
    - **EvidenceBody**: Evidence summaries with quality ratings
    - **ClinicalModule**: Clinical topic modules

    Returns ranked results with similarity scores and execution metadata.
    """
    start_time = time.perf_counter()

    try:
        records, embedding_time_ms, search_time_ms = neo4j.vector_search_with_embedding(
            query_text=request.query,
            node_type=request.node_type.value,
            top_k=request.top_k,
        )
    except ServiceUnavailable:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable. Please try again later.",
        ) from None
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Search failed: {str(e)}",
        ) from None

    # Convert records to appropriate result models
    results = []
    for record in records:
        try:
            result = _build_result(request.node_type, record)
            results.append(result)
        except (KeyError, TypeError):
            # Skip malformed records but log in production
            continue

    total_time_ms = int((time.perf_counter() - start_time) * 1000)

    reasoning = ReasoningBlock(
        path_used="vector",
        embedding_time_ms=embedding_time_ms,
        search_time_ms=search_time_ms,
        total_time_ms=total_time_ms,
        node_type_searched=request.node_type.value,
        results_count=len(results),
    )

    return VectorSearchResponse(results=results, reasoning=reasoning)


@router.get(
    "/node-types",
    summary="List supported node types",
    description="Returns the list of node types available for vector search",
    tags=["search"],
)
async def list_node_types(
    neo4j: Annotated[Neo4jService, Depends(get_neo4j_service)],
):
    """List all node types that support vector search."""
    return {
        "node_types": neo4j.get_supported_node_types(),
        "default": "Recommendation",
    }


# ============================================================
# Graph Search Endpoints
# ============================================================

@router.post(
    "/graph",
    response_model=GraphSearchResponse,
    summary="Template-based graph traversal",
    description="Execute predefined graph query templates with parameters",
    responses={
        200: {"description": "Successful query with results"},
        400: {"description": "Unknown template"},
        422: {"description": "Invalid or missing parameters"},
        503: {"description": "Database unavailable"},
    },
)
async def graph_search(
    request: GraphSearchRequest,
    neo4j: Annotated[Neo4jService, Depends(get_neo4j_service)],
) -> GraphSearchResponse:
    """
    Execute a predefined graph query template.

    Available templates:
    - **recommendation_only**: Fetch recommendations by ID list
    - **recommendation_with_evidence**: Recommendations with quality ratings
    - **evidence_chain_full**: Complete trail from recommendation to studies
    - **studies_for_recommendation**: All studies supporting a recommendation
    - **recommendations_by_topic**: Filter recommendations by topic

    Use GET /api/v1/search/templates to see all templates and their parameters.
    """
    start_time = time.perf_counter()

    # Validate template exists
    template = get_template(request.template)
    if template is None:
        valid_templates = list(TEMPLATES.keys())
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown template: '{request.template}'. Valid templates: {valid_templates}",
        )

    # Validate parameters
    param_errors = validate_params(template, request.params)
    if param_errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Parameter validation failed: {'; '.join(param_errors)}",
        )

    # Execute query
    try:
        records, query_time_ms = neo4j.execute_graph_query(
            cypher=template.cypher,
            params=request.params,
        )
    except ServiceUnavailable:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable. Please try again later.",
        ) from None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Query failed: {str(e)}",
        ) from None

    total_time_ms = int((time.perf_counter() - start_time) * 1000)

    reasoning = GraphReasoningBlock(
        template_used=request.template,
        query_time_ms=query_time_ms,
        total_time_ms=total_time_ms,
        results_count=len(records),
    )

    return GraphSearchResponse(results=records, reasoning=reasoning)


@router.get(
    "/templates",
    response_model=list[TemplateInfo],
    summary="List available graph templates",
    description="Returns all available graph query templates with their parameters",
    tags=["search"],
)
async def list_graph_templates():
    """List all available graph query templates."""
    return list_templates()
