"""Pydantic models for answer generation endpoint."""

from pydantic import BaseModel, Field


class AnswerRequest(BaseModel):
    """Request body for answer generation endpoint."""

    question: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Natural language question about diabetes care",
        json_schema_extra={"example": "What medications are recommended for patients with diabetes and kidney disease?"}
    )
    include_citations: bool = Field(
        default=True,
        description="Whether to include detailed citations in the response"
    )
    include_studies: bool = Field(
        default=False,
        description="Whether to include supporting study details"
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of recommendations to use as context"
    )


class Citation(BaseModel):
    """A citation to a specific recommendation."""

    rec_id: str = Field(..., description="Recommendation ID")
    rec_text: str = Field(..., description="Full recommendation text")
    strength: str | None = Field(None, description="Recommendation strength (Strong, Weak)")
    direction: str | None = Field(None, description="Recommendation direction (For, Against)")
    topic: str | None = Field(None, description="Clinical topic")


class StudyCitation(BaseModel):
    """A citation to a supporting study."""

    pmid: str | None = Field(None, description="PubMed ID")
    title: str = Field(..., description="Study title")
    journal: str | None = Field(None, description="Journal name")
    year: int | None = Field(None, description="Publication year")


class AnswerReasoning(BaseModel):
    """Metadata about answer generation."""

    query_routing: str = Field(..., description="How the query was routed (VECTOR, GRAPH, HYBRID)")
    results_retrieved: int = Field(..., description="Number of recommendations retrieved")
    results_used: int = Field(..., description="Number of recommendations used in answer")
    generation_time_ms: int = Field(..., description="Time to generate answer")
    total_time_ms: int = Field(..., description="Total request processing time")
    model_used: str = Field(..., description="LLM model used for generation")
    tokens_used: dict = Field(
        default_factory=dict,
        description="Token usage breakdown",
        json_schema_extra={"example": {"prompt": 2400, "completion": 350}}
    )


class AnswerResponse(BaseModel):
    """Response from the answer generation endpoint."""

    answer: str = Field(..., description="Natural language answer with citations")
    citations: list[Citation] = Field(
        default_factory=list,
        description="Recommendations cited in the answer"
    )
    studies_cited: list[StudyCitation] = Field(
        default_factory=list,
        description="Studies supporting the recommendations"
    )
    reasoning: AnswerReasoning = Field(..., description="Generation metadata")

    model_config = {
        "json_schema_extra": {
            "example": {
                "answer": "Based on the VA/DoD Clinical Practice Guideline, for patients with type 2 diabetes and chronic kidney disease, **SGLT2 inhibitors are strongly recommended** (Recommendation 22). This is a Strong recommendation For their use, supported by high-quality evidence from 34 studies.\n\nThe guideline specifically states that SGLT2 inhibitors provide both cardiovascular and renal protective benefits in this population.",
                "citations": [
                    {
                        "rec_id": "REC_022",
                        "rec_text": "For adults with T2DM and CKD, we recommend SGLT2 inhibitors...",
                        "strength": "Strong",
                        "direction": "For",
                        "topic": "Pharmacotherapy"
                    }
                ],
                "studies_cited": [
                    {
                        "pmid": "30990260",
                        "title": "Canagliflozin and Renal Outcomes in Type 2 Diabetes",
                        "journal": "N Engl J Med",
                        "year": 2019
                    }
                ],
                "reasoning": {
                    "query_routing": "HYBRID",
                    "results_retrieved": 10,
                    "results_used": 3,
                    "generation_time_ms": 1200,
                    "total_time_ms": 1650,
                    "model_used": "claude-3-5-sonnet-20241022",
                    "tokens_used": {"prompt": 2400, "completion": 350}
                }
            }
        }
    }
