"""Pydantic models for unified query endpoint."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class QueryType(str, Enum):
    """Types of query routing decisions."""
    VECTOR = "VECTOR"
    GRAPH = "GRAPH"
    HYBRID = "HYBRID"


class Intent(str, Enum):
    """Query intent classifications."""
    TREATMENT_RECOMMENDATION = "treatment_recommendation"
    EVIDENCE_LOOKUP = "evidence_lookup"
    DRUG_INFO = "drug_info"
    SAFETY_CHECK = "safety_check"
    GENERAL_QUESTION = "general_question"


class QueryRequest(BaseModel):
    """Request body for unified query endpoint."""

    question: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Natural language question about diabetes care",
        json_schema_extra={"example": "What medications are recommended for patients with diabetes and kidney disease?"}
    )
    include_studies: bool = Field(
        default=False,
        description="Whether to include supporting studies in the response"
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of results to return"
    )


class ExtractedEntities(BaseModel):
    """Entities extracted from the query by the router."""

    conditions: list[str] = Field(default_factory=list, description="Medical conditions mentioned")
    medications: list[str] = Field(default_factory=list, description="Medications mentioned")
    patient_characteristics: list[str] = Field(default_factory=list, description="Patient characteristics (age, comorbidities)")
    rec_ids: list[str] = Field(default_factory=list, description="Specific recommendation IDs mentioned")
    topics: list[str] = Field(default_factory=list, description="Clinical topics mentioned")


class RoutingDecision(BaseModel):
    """The router's decision on how to handle the query."""

    query_type: QueryType = Field(..., description="Selected query strategy")
    intent: Intent = Field(..., description="Classified intent of the query")
    confidence: float = Field(..., ge=0, le=1, description="Router confidence in the decision")
    entities: ExtractedEntities = Field(default_factory=ExtractedEntities, description="Extracted entities")
    template_hint: str | None = Field(None, description="Suggested graph template if query_type is GRAPH")
    reasoning: str = Field(..., description="Brief explanation of routing decision")


class TimingInfo(BaseModel):
    """Timing breakdown for query execution."""

    routing_ms: int = Field(..., description="Time for LLM routing decision")
    embedding_ms: int | None = Field(None, description="Time for query embedding (if vector path used)")
    vector_search_ms: int | None = Field(None, description="Time for vector search (if used)")
    graph_search_ms: int | None = Field(None, description="Time for graph traversal (if used)")
    fusion_ms: int | None = Field(None, description="Time for result fusion (if hybrid)")
    rerank_ms: int | None = Field(None, description="Time for re-ranking")
    total_ms: int = Field(..., description="Total request processing time")


class QueryReasoningBlock(BaseModel):
    """Full reasoning and metadata about query execution."""

    routing: RoutingDecision = Field(..., description="How the query was routed")
    paths_used: list[Literal["vector", "graph"]] = Field(..., description="Retrieval paths executed")
    template_used: str | None = Field(None, description="Graph template used (if any)")
    vector_candidates: int | None = Field(None, description="Number of vector search results")
    graph_candidates: int | None = Field(None, description="Number of graph query results")
    fusion_method: str | None = Field(None, description="Fusion method used (if hybrid)")
    rerank_applied: bool = Field(default=False, description="Whether re-ranking was applied")
    timing: TimingInfo = Field(..., description="Execution timing breakdown")


class QueryResult(BaseModel):
    """A single result from the unified query."""

    rec_id: str = Field(..., description="Recommendation ID")
    rec_text: str = Field(..., description="Full recommendation text")
    strength: str | None = Field(None, description="Recommendation strength")
    direction: str | None = Field(None, description="Recommendation direction")
    topic: str | None = Field(None, description="Clinical topic")
    score: float = Field(..., description="Combined relevance score")
    evidence_quality: str | None = Field(None, description="Evidence quality rating")
    study_count: int | None = Field(None, description="Number of supporting studies")
    source: Literal["vector", "graph", "both"] = Field(..., description="Which path(s) found this result")


class QueryResponse(BaseModel):
    """Response from the unified query endpoint."""

    results: list[QueryResult] = Field(..., description="Ranked list of relevant recommendations")
    reasoning: QueryReasoningBlock = Field(..., description="Full execution metadata")

    model_config = {
        "json_schema_extra": {
            "example": {
                "results": [
                    {
                        "rec_id": "REC_022",
                        "rec_text": "For adults with type 2 diabetes mellitus and chronic kidney disease...",
                        "strength": "Strong",
                        "direction": "For",
                        "topic": "Pharmacotherapy",
                        "score": 0.92,
                        "evidence_quality": "High",
                        "study_count": 34,
                        "source": "both"
                    }
                ],
                "reasoning": {
                    "routing": {
                        "query_type": "HYBRID",
                        "intent": "treatment_recommendation",
                        "confidence": 0.95,
                        "entities": {
                            "conditions": ["type 2 diabetes", "chronic kidney disease"],
                            "medications": [],
                            "patient_characteristics": [],
                            "rec_ids": [],
                            "topics": ["Pharmacotherapy"]
                        },
                        "template_hint": "recommendations_by_topic",
                        "reasoning": "Patient-specific treatment question with comorbidities warrants hybrid search"
                    },
                    "paths_used": ["vector", "graph"],
                    "template_used": "recommendations_by_topic",
                    "vector_candidates": 10,
                    "graph_candidates": 8,
                    "fusion_method": "RRF",
                    "rerank_applied": True,
                    "timing": {
                        "routing_ms": 245,
                        "embedding_ms": 89,
                        "vector_search_ms": 45,
                        "graph_search_ms": 67,
                        "fusion_ms": 3,
                        "rerank_ms": 2,
                        "total_ms": 451
                    }
                }
            }
        }
    }
