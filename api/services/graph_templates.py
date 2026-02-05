"""Graph query templates for structural traversal.

All templates use parameterized Cypher queries to prevent injection.
Templates are validated against an allowlist before execution.
"""

from typing import Any

from pydantic import BaseModel


class TemplateParam(BaseModel):
    """Schema for a template parameter."""
    name: str
    type: str  # "string", "string_list", "int"
    required: bool = True
    description: str


class GraphTemplate(BaseModel):
    """Definition of a graph query template."""
    name: str
    description: str
    use_case: str
    params: list[TemplateParam]
    cypher: str


# Template definitions
TEMPLATES: dict[str, GraphTemplate] = {
    "recommendation_only": GraphTemplate(
        name="recommendation_only",
        description="Fetch recommendations by ID list",
        use_case="Retrieve specific recommendations by ID",
        params=[
            TemplateParam(
                name="rec_ids",
                type="string_list",
                required=True,
                description="List of recommendation IDs to fetch"
            )
        ],
        cypher="""
            MATCH (r:Recommendation)
            WHERE r.rec_id IN $rec_ids
            RETURN r.rec_id AS rec_id,
                   r.rec_text AS rec_text,
                   r.strength AS strength,
                   r.direction AS direction,
                   r.topic AS topic,
                   r.subtopic AS subtopic,
                   r.rec_number AS rec_number
            ORDER BY r.rec_number
        """
    ),

    "recommendation_with_evidence": GraphTemplate(
        name="recommendation_with_evidence",
        description="Recommendations with evidence quality context",
        use_case="Show recommendations with quality ratings and study counts",
        params=[
            TemplateParam(
                name="rec_ids",
                type="string_list",
                required=True,
                description="List of recommendation IDs to fetch"
            )
        ],
        cypher="""
            MATCH (r:Recommendation)-[:BASED_ON]->(eb:EvidenceBody)
            WHERE r.rec_id IN $rec_ids
            RETURN r.rec_id AS rec_id,
                   r.rec_text AS rec_text,
                   r.strength AS strength,
                   r.direction AS direction,
                   r.topic AS topic,
                   eb.evidence_id AS evidence_id,
                   eb.quality_rating AS quality_rating,
                   eb.num_studies AS num_studies,
                   eb.key_findings AS key_findings
            ORDER BY r.rec_number
        """
    ),

    "evidence_chain_full": GraphTemplate(
        name="evidence_chain_full",
        description="Full citation chain from recommendation to studies",
        use_case="Physician wants to see complete supporting evidence trail",
        params=[
            TemplateParam(
                name="rec_ids",
                type="string_list",
                required=True,
                description="List of recommendation IDs to trace"
            )
        ],
        cypher="""
            MATCH (r:Recommendation)-[:BASED_ON]->(eb:EvidenceBody)
                  -[:ANSWERS]->(kq:KeyQuestion)
            WHERE r.rec_id IN $rec_ids
            OPTIONAL MATCH (eb)-[:INCLUDES]->(s:Study)
            WITH r, eb, kq, s
            ORDER BY s.year DESC
            WITH r, eb, kq, collect(CASE WHEN s IS NOT NULL THEN {
                study_id: s.study_id,
                title: s.title,
                pmid: s.pmid,
                journal: s.journal,
                year: s.year,
                study_type: s.study_type
            } END) AS studies
            RETURN r.rec_id AS rec_id,
                   r.rec_text AS rec_text,
                   r.strength AS strength,
                   r.direction AS direction,
                   r.topic AS topic,
                   {
                       evidence_id: eb.evidence_id,
                       quality_rating: eb.quality_rating,
                       num_studies: eb.num_studies,
                       key_findings: eb.key_findings
                   } AS evidence,
                   {
                       kq_id: kq.kq_id,
                       question_text: kq.question_text,
                       kq_number: kq.kq_number
                   } AS key_question,
                   studies
            ORDER BY r.rec_number
        """
    ),

    "studies_for_recommendation": GraphTemplate(
        name="studies_for_recommendation",
        description="All studies supporting a specific recommendation",
        use_case="Deep dive into evidence base for a single recommendation",
        params=[
            TemplateParam(
                name="rec_id",
                type="string",
                required=True,
                description="Single recommendation ID"
            )
        ],
        cypher="""
            MATCH (r:Recommendation {rec_id: $rec_id})
                  -[:BASED_ON]->(eb:EvidenceBody)
                  -[:INCLUDES]->(s:Study)
            RETURN s.study_id AS study_id,
                   s.title AS title,
                   s.pmid AS pmid,
                   s.journal AS journal,
                   s.year AS year,
                   s.study_type AS study_type,
                   s.authors AS authors,
                   s.abstract AS abstract
            ORDER BY s.year DESC
        """
    ),

    "recommendations_by_topic": GraphTemplate(
        name="recommendations_by_topic",
        description="Filter recommendations by topic",
        use_case="Browse recommendations by clinical category",
        params=[
            TemplateParam(
                name="topic",
                type="string",
                required=True,
                description="Topic to search for (case-insensitive partial match)"
            )
        ],
        cypher="""
            MATCH (r:Recommendation)
            WHERE toLower(r.topic) CONTAINS toLower($topic)
               OR (r.subtopic IS NOT NULL AND toLower(r.subtopic) CONTAINS toLower($topic))
            RETURN r.rec_id AS rec_id,
                   r.rec_text AS rec_text,
                   r.strength AS strength,
                   r.direction AS direction,
                   r.topic AS topic,
                   r.subtopic AS subtopic,
                   r.rec_number AS rec_number
            ORDER BY r.rec_number
        """
    ),
}


def get_template(name: str) -> GraphTemplate | None:
    """Get a template by name."""
    return TEMPLATES.get(name)


def list_templates() -> list[dict[str, Any]]:
    """List all available templates with their metadata."""
    return [
        {
            "name": t.name,
            "description": t.description,
            "use_case": t.use_case,
            "params": [p.model_dump() for p in t.params],
        }
        for t in TEMPLATES.values()
    ]


def validate_params(template: GraphTemplate, params: dict[str, Any]) -> list[str]:
    """
    Validate parameters against template schema.

    Returns list of error messages (empty if valid).
    """
    errors = []

    for param_schema in template.params:
        param_name = param_schema.name
        param_value = params.get(param_name)

        # Check required params
        if param_schema.required and param_value is None:
            errors.append(f"Missing required parameter: {param_name}")
            continue

        if param_value is None:
            continue

        # Type validation
        if param_schema.type == "string":
            if not isinstance(param_value, str):
                errors.append(f"Parameter '{param_name}' must be a string")
            elif len(param_value.strip()) == 0:
                errors.append(f"Parameter '{param_name}' cannot be empty")

        elif param_schema.type == "string_list":
            if not isinstance(param_value, list):
                errors.append(f"Parameter '{param_name}' must be a list")
            elif len(param_value) == 0:
                errors.append(f"Parameter '{param_name}' cannot be empty")
            elif not all(isinstance(item, str) for item in param_value):
                errors.append(f"Parameter '{param_name}' must be a list of strings")

        elif param_schema.type == "int":
            if not isinstance(param_value, int):
                errors.append(f"Parameter '{param_name}' must be an integer")

    return errors
