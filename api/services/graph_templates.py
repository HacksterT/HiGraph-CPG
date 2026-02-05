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

    # ============================================================
    # V2 Templates - CarePhase, Condition, Intervention
    # ============================================================

    "recommendations_by_care_phase": GraphTemplate(
        name="recommendations_by_care_phase",
        description="Filter recommendations by care phase",
        use_case="Browse recommendations by phase of care (screening, diagnosis, treatment, etc.)",
        params=[
            TemplateParam(
                name="phase_name",
                type="string",
                required=True,
                description="Care phase name (case-insensitive partial match)"
            )
        ],
        cypher="""
            MATCH (r:Recommendation)-[:BELONGS_TO]->(cp:CarePhase)
            WHERE toLower(cp.name) CONTAINS toLower($phase_name)
            RETURN r.rec_id AS rec_id,
                   r.rec_text AS rec_text,
                   r.strength AS strength,
                   r.direction AS direction,
                   r.topic AS topic,
                   cp.phase_id AS phase_id,
                   cp.name AS phase_name,
                   cp.description AS phase_description
            ORDER BY r.rec_number
        """
    ),

    "recommendations_by_condition": GraphTemplate(
        name="recommendations_by_condition",
        description="Filter recommendations by condition/comorbidity",
        use_case="Find recommendations for patients with specific conditions (CKD, CVD, etc.)",
        params=[
            TemplateParam(
                name="condition_name",
                type="string",
                required=True,
                description="Condition name (case-insensitive partial match)"
            )
        ],
        cypher="""
            MATCH (r:Recommendation)-[rel:APPLIES_TO|RELEVANT_TO]->(c:Condition)
            WHERE toLower(c.name) CONTAINS toLower($condition_name)
               OR toLower(c.condition_id) CONTAINS toLower($condition_name)
            RETURN r.rec_id AS rec_id,
                   r.rec_text AS rec_text,
                   r.strength AS strength,
                   r.direction AS direction,
                   r.topic AS topic,
                   c.condition_id AS condition_id,
                   c.name AS condition_name,
                   type(rel) AS relationship_type
            ORDER BY r.rec_number
        """
    ),

    "recommendations_by_intervention": GraphTemplate(
        name="recommendations_by_intervention",
        description="Filter recommendations by intervention/medication",
        use_case="Find recommendations about specific interventions (SGLT2i, GLP-1 RA, metformin, etc.)",
        params=[
            TemplateParam(
                name="intervention_name",
                type="string",
                required=True,
                description="Intervention name (case-insensitive partial match)"
            )
        ],
        cypher="""
            MATCH (r:Recommendation)-[:RECOMMENDS]->(i:Intervention)
            WHERE toLower(i.name) CONTAINS toLower($intervention_name)
               OR toLower(i.intervention_id) CONTAINS toLower($intervention_name)
               OR (i.category IS NOT NULL AND toLower(i.category) CONTAINS toLower($intervention_name))
            RETURN r.rec_id AS rec_id,
                   r.rec_text AS rec_text,
                   r.strength AS strength,
                   r.direction AS direction,
                   r.topic AS topic,
                   i.intervention_id AS intervention_id,
                   i.name AS intervention_name,
                   i.category AS intervention_category
            ORDER BY r.rec_number
        """
    ),

    "disease_progression": GraphTemplate(
        name="disease_progression",
        description="Show disease progression paths from a condition",
        use_case="Understand what conditions can develop from a given condition",
        params=[
            TemplateParam(
                name="condition_name",
                type="string",
                required=True,
                description="Starting condition name (case-insensitive partial match)"
            )
        ],
        cypher="""
            MATCH (c1:Condition)
            WHERE toLower(c1.name) CONTAINS toLower($condition_name)
            OPTIONAL MATCH (c1)-[r:MAY_DEVELOP|PRECURSOR_TO|ASSOCIATED_WITH]->(c2:Condition)
            RETURN c1.condition_id AS source_id,
                   c1.name AS source_name,
                   c1.icd10_codes AS source_icd10,
                   type(r) AS relationship,
                   c2.condition_id AS target_id,
                   c2.name AS target_name,
                   c2.icd10_codes AS target_icd10
            ORDER BY c1.name, type(r), c2.name
        """
    ),

    "care_phases_overview": GraphTemplate(
        name="care_phases_overview",
        description="List all care phases with recommendation counts",
        use_case="UI navigation - show available care phases for browsing",
        params=[],
        cypher="""
            MATCH (cp:CarePhase)
            OPTIONAL MATCH (r:Recommendation)-[:BELONGS_TO]->(cp)
            WITH cp, count(r) AS rec_count
            RETURN cp.phase_id AS phase_id,
                   cp.name AS name,
                   cp.description AS description,
                   cp.order_index AS order_index,
                   rec_count
            ORDER BY cp.order_index
        """
    ),

    "conditions_overview": GraphTemplate(
        name="conditions_overview",
        description="List all conditions with recommendation counts",
        use_case="UI navigation - show available conditions for filtering",
        params=[],
        cypher="""
            MATCH (c:Condition)
            OPTIONAL MATCH (r:Recommendation)-[:APPLIES_TO|RELEVANT_TO]->(c)
            WITH c, count(DISTINCT r) AS rec_count
            RETURN c.condition_id AS condition_id,
                   c.name AS name,
                   c.category AS category,
                   c.icd10_codes AS icd10_codes,
                   rec_count
            ORDER BY rec_count DESC, c.name
        """
    ),

    "interventions_overview": GraphTemplate(
        name="interventions_overview",
        description="List all interventions with recommendation counts",
        use_case="UI navigation - show available interventions for filtering",
        params=[],
        cypher="""
            MATCH (i:Intervention)
            OPTIONAL MATCH (r:Recommendation)-[:RECOMMENDS]->(i)
            WITH i, count(DISTINCT r) AS rec_count
            RETURN i.intervention_id AS intervention_id,
                   i.name AS name,
                   i.category AS category,
                   i.mechanism AS mechanism,
                   rec_count
            ORDER BY rec_count DESC, i.name
        """
    ),

    "interventions_for_recommendation": GraphTemplate(
        name="interventions_for_recommendation",
        description="Get interventions recommended by a specific recommendation",
        use_case="Evidence chain enrichment - see what interventions a recommendation covers",
        params=[
            TemplateParam(
                name="rec_id",
                type="string",
                required=True,
                description="Single recommendation ID"
            )
        ],
        cypher="""
            MATCH (r:Recommendation {rec_id: $rec_id})-[:RECOMMENDS]->(i:Intervention)
            RETURN i.intervention_id AS intervention_id,
                   i.name AS name,
                   i.category AS category,
                   i.mechanism AS mechanism,
                   r.rec_id AS rec_id,
                   r.strength AS strength,
                   r.direction AS direction
            ORDER BY i.name
        """
    ),

    "conditions_for_recommendation": GraphTemplate(
        name="conditions_for_recommendation",
        description="Get conditions that a recommendation applies to",
        use_case="Evidence chain enrichment - see what conditions a recommendation addresses",
        params=[
            TemplateParam(
                name="rec_id",
                type="string",
                required=True,
                description="Single recommendation ID"
            )
        ],
        cypher="""
            MATCH (r:Recommendation {rec_id: $rec_id})-[rel:APPLIES_TO|RELEVANT_TO]->(c:Condition)
            RETURN c.condition_id AS condition_id,
                   c.name AS name,
                   c.category AS category,
                   c.icd10_codes AS icd10_codes,
                   type(rel) AS relationship_type,
                   r.rec_id AS rec_id
            ORDER BY type(rel), c.name
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
