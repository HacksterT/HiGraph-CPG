"""Pydantic models for search endpoints."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Supported node types for vector search."""
    RECOMMENDATION = "Recommendation"
    STUDY = "Study"
    KEY_QUESTION = "KeyQuestion"
    EVIDENCE_BODY = "EvidenceBody"
    CLINICAL_MODULE = "ClinicalModule"


class VectorSearchRequest(BaseModel):
    """Request body for vector similarity search."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Natural language query text to search for",
        json_schema_extra={"example": "medications for diabetic patients with kidney disease"}
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of results to return (1-50)"
    )
    node_type: NodeType = Field(
        default=NodeType.RECOMMENDATION,
        description="Node type to search"
    )


# Node-type specific result models

class RecommendationResult(BaseModel):
    """Search result for Recommendation nodes."""
    node_type: Literal["Recommendation"] = "Recommendation"
    rec_id: str = Field(..., description="Recommendation ID")
    rec_text: str = Field(..., description="Full recommendation text")
    strength: str | None = Field(None, description="Recommendation strength (Strong, Weak, Neither)")
    direction: str | None = Field(None, description="Recommendation direction (For, Against, Neither)")
    topic: str | None = Field(None, description="Clinical topic category")
    similarity_score: float = Field(..., ge=0, le=1, description="Cosine similarity score")


class StudyResult(BaseModel):
    """Search result for Study nodes."""
    node_type: Literal["Study"] = "Study"
    study_id: str = Field(..., description="Study ID")
    title: str = Field(..., description="Study title")
    abstract: str | None = Field(None, description="Study abstract")
    authors: str | None = Field(None, description="Study authors")
    journal: str | None = Field(None, description="Journal name")
    year: int | None = Field(None, description="Publication year")
    pmid: str | None = Field(None, description="PubMed ID")
    study_type: str | None = Field(None, description="Type of study (RCT, meta-analysis, etc.)")
    similarity_score: float = Field(..., ge=0, le=1, description="Cosine similarity score")


class KeyQuestionResult(BaseModel):
    """Search result for KeyQuestion nodes."""
    node_type: Literal["KeyQuestion"] = "KeyQuestion"
    kq_id: str = Field(..., description="Key Question ID")
    question_text: str = Field(..., description="The key question text")
    kq_number: int | None = Field(None, description="Key question number")
    population: str | None = Field(None, description="Target population")
    intervention: str | None = Field(None, description="Intervention being studied")
    similarity_score: float = Field(..., ge=0, le=1, description="Cosine similarity score")


class EvidenceBodyResult(BaseModel):
    """Search result for EvidenceBody nodes."""
    node_type: Literal["EvidenceBody"] = "EvidenceBody"
    evidence_id: str = Field(..., description="Evidence Body ID")
    key_findings: str = Field(..., description="Key findings summary")
    quality_rating: str | None = Field(None, description="Evidence quality rating")
    num_studies: int | None = Field(None, description="Number of supporting studies")
    similarity_score: float = Field(..., ge=0, le=1, description="Cosine similarity score")


class ClinicalModuleResult(BaseModel):
    """Search result for ClinicalModule nodes."""
    node_type: Literal["ClinicalModule"] = "ClinicalModule"
    module_id: str = Field(..., description="Module ID")
    module_name: str = Field(..., description="Module name")
    description: str | None = Field(None, description="Module description")
    topics: str | None = Field(None, description="Topics covered")
    similarity_score: float = Field(..., ge=0, le=1, description="Cosine similarity score")


# Union type for any search result
SearchResult = (
    RecommendationResult
    | StudyResult
    | KeyQuestionResult
    | EvidenceBodyResult
    | ClinicalModuleResult
)


class ReasoningBlock(BaseModel):
    """Metadata about query execution for transparency."""

    path_used: str = Field(..., description="Retrieval path used (vector, graph, hybrid)")
    embedding_time_ms: int | None = Field(None, description="Time to generate query embedding")
    search_time_ms: int | None = Field(None, description="Time to execute search")
    total_time_ms: int = Field(..., description="Total request processing time")
    node_type_searched: str = Field(default="Recommendation", description="Node type that was searched")
    results_count: int = Field(..., description="Number of results returned")


class VectorSearchResponse(BaseModel):
    """Response from vector similarity search endpoint."""

    results: list[SearchResult] = Field(
        ...,
        description="Ranked list of matching nodes"
    )
    reasoning: ReasoningBlock = Field(
        ...,
        description="Execution metadata for transparency"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "results": [
                    {
                        "node_type": "Recommendation",
                        "rec_id": "CPG_DM_2023_REC_022",
                        "rec_text": "For adults with type 2 diabetes mellitus and chronic kidney disease...",
                        "strength": "Strong",
                        "direction": "For",
                        "topic": "Pharmacotherapy",
                        "similarity_score": 0.85
                    }
                ],
                "reasoning": {
                    "path_used": "vector",
                    "embedding_time_ms": 89,
                    "search_time_ms": 45,
                    "total_time_ms": 134,
                    "node_type_searched": "Recommendation",
                    "results_count": 1
                }
            }
        }
    }


# ============================================================
# Graph Search Models
# ============================================================

class GraphSearchRequest(BaseModel):
    """Request body for template-based graph traversal."""

    template: str = Field(
        ...,
        description="Name of the graph query template to execute",
        json_schema_extra={"example": "evidence_chain_full"}
    )
    params: dict = Field(
        default_factory=dict,
        description="Parameters for the template",
        json_schema_extra={"example": {"rec_ids": ["CPG_DM_2023_REC_022"]}}
    )


class GraphReasoningBlock(BaseModel):
    """Metadata about graph query execution."""

    path_used: Literal["graph"] = "graph"
    template_used: str = Field(..., description="Name of template executed")
    query_time_ms: int = Field(..., description="Time to execute Cypher query")
    total_time_ms: int = Field(..., description="Total request processing time")
    results_count: int = Field(..., description="Number of results returned")


class GraphSearchResponse(BaseModel):
    """Response from graph traversal endpoint."""

    results: list[dict] = Field(
        ...,
        description="Query results (structure depends on template)"
    )
    reasoning: GraphReasoningBlock = Field(
        ...,
        description="Execution metadata for transparency"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "results": [
                    {
                        "rec_id": "CPG_DM_2023_REC_022",
                        "rec_text": "For adults with type 2 diabetes mellitus...",
                        "strength": "Strong",
                        "direction": "For",
                        "topic": "Pharmacotherapy",
                        "evidence": {
                            "evidence_id": "CPG_DM_2023_EVB_007",
                            "quality_rating": "High",
                            "num_studies": 9
                        },
                        "key_question": {
                            "kq_id": "CPG_DM_2023_KQ_007",
                            "question_text": "In adults with T2DM..."
                        },
                        "studies": [
                            {"title": "EMPA-REG OUTCOME", "pmid": "26378978", "year": 2015}
                        ]
                    }
                ],
                "reasoning": {
                    "path_used": "graph",
                    "template_used": "evidence_chain_full",
                    "query_time_ms": 67,
                    "total_time_ms": 72,
                    "results_count": 1
                }
            }
        }
    }


class TemplateInfo(BaseModel):
    """Information about an available graph template."""

    name: str = Field(..., description="Template name")
    description: str = Field(..., description="What the template does")
    use_case: str = Field(..., description="When to use this template")
    params: list[dict] = Field(..., description="Required and optional parameters")
