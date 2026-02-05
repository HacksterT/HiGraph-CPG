"""
Extraction Template: Evidence Bodies

Provides prompt templates and JSON schemas for extracting evidence synthesis
and GRADE quality ratings from CPG Appendix A sections.
"""

from typing import Dict, Any, List, Optional


EVIDENCE_BODY_SCHEMA = {
    "type": "object",
    "required": ["kq_number", "topic", "quality_rating", "key_findings"],
    "properties": {
        "kq_number": {
            "type": "integer",
            "description": "Key question number this evidence body addresses"
        },
        "topic": {
            "type": "string",
            "description": "Topic area"
        },
        "quality_rating": {
            "type": "string",
            "enum": ["High", "Moderate", "Low", "Very Low"],
            "description": "Overall GRADE quality of evidence rating"
        },
        "confidence_level": {
            "type": "string",
            "description": "Confidence statement about the evidence"
        },
        "num_studies": {
            "type": "integer",
            "description": "Number of studies in this evidence body"
        },
        "study_types": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Types of studies included (RCT, SR, Cohort, etc.)"
        },
        "population_description": {
            "type": "string",
            "description": "Description of the population studied"
        },
        "key_findings": {
            "type": "string",
            "description": "Summary of key findings from the evidence synthesis"
        },
        "limitations": {
            "type": ["string", "null"],
            "description": "Key limitations of the evidence"
        },
        "reference_numbers": {
            "type": "array",
            "items": {"type": "integer"},
            "description": "Reference numbers cited in this evidence body"
        }
    }
}


def get_schema() -> dict:
    """Return the JSON schema for evidence body extraction."""
    return EVIDENCE_BODY_SCHEMA


def create_extraction_prompt(
    section_text: str,
    config: Optional[Any] = None,
) -> str:
    """
    Create extraction prompt for evidence body from Appendix A text.

    Args:
        section_text: Text of the evidence synthesis section
        config: Optional GuidelineConfig

    Returns:
        Formatted prompt string for LLM
    """
    guideline_name = "VA/DoD Clinical Practice Guideline"
    if config:
        guideline_name = config.full_title

    prompt = f"""You are extracting evidence body summaries from the {guideline_name}.

INPUT TEXT (from Appendix A evidence synthesis):
{section_text}

TASK: Extract the evidence body (evidence synthesis) for each Key Question section.

Each Key Question in Appendix A is followed by an evidence synthesis that summarizes what the
systematic review found. Extract one evidence body per Key Question.

OUTPUT FORMAT: Return a JSON array of evidence body objects. Each object must have:
- kq_number: (integer) the key question number this evidence addresses
- topic: (string) topic area
- quality_rating: (string) GRADE quality rating, must be exactly one of: "High", "Moderate", "Low", "Very Low"
- confidence_level: (string) confidence statement (e.g., "Moderate confidence that...")
- num_studies: (integer) number of studies included in the evidence synthesis
- study_types: (array of strings) types of studies (e.g., ["RCT", "Systematic Review"])
- population_description: (string) who was studied
- key_findings: (string) summary of the main findings from the evidence synthesis
- limitations: (string or null) key limitations mentioned
- reference_numbers: (array of integers) reference numbers cited in this section

CRITICAL RULES:
1. GRADE ratings must match exactly: "High", "Moderate", "Low", or "Very Low"
2. Extract key_findings as a coherent summary, not just copy-paste
3. Count studies based on explicit mentions in the text
4. reference_numbers should include all bracketed reference numbers (e.g., [45], [67-89])
5. One evidence body per Key Question
6. Return ONLY the JSON array, no markdown, no explanation

Example output format:
[
  {{
    "kq_number": 1,
    "topic": "Prediabetes interventions",
    "quality_rating": "Moderate",
    "confidence_level": "Moderate confidence that lifestyle interventions reduce progression to T2DM",
    "num_studies": 15,
    "study_types": ["RCT", "Systematic Review"],
    "population_description": "Adults with prediabetes (HbA1c 5.7-6.4%)",
    "key_findings": "Structured lifestyle interventions reduced progression to T2DM by 58% compared to placebo...",
    "limitations": "Most studies had follow-up less than 5 years",
    "reference_numbers": [12, 15, 23, 45, 67]
  }}
]

Extract the evidence bodies now. Return only valid JSON."""

    return prompt


def validate(eb_data: Dict[str, Any]) -> tuple:
    """
    Validate extracted evidence body against schema and business rules.

    Args:
        eb_data: Extracted evidence body dictionary

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    required = ['kq_number', 'topic', 'quality_rating', 'key_findings']
    for f in required:
        if f not in eb_data:
            errors.append(f"Missing required field: {f}")

    valid_ratings = ['High', 'Moderate', 'Low', 'Very Low']
    if 'quality_rating' in eb_data and eb_data['quality_rating'] not in valid_ratings:
        errors.append(f"Invalid quality_rating: {eb_data['quality_rating']}. Must be one of {valid_ratings}")

    if 'key_findings' in eb_data and len(str(eb_data['key_findings'])) < 20:
        errors.append(f"key_findings too short: {len(eb_data['key_findings'])} chars")

    if 'kq_number' in eb_data:
        if not isinstance(eb_data['kq_number'], int) or eb_data['kq_number'] < 1:
            errors.append(f"Invalid kq_number: {eb_data['kq_number']}")

    if 'num_studies' in eb_data and eb_data['num_studies'] is not None:
        if not isinstance(eb_data['num_studies'], int) or eb_data['num_studies'] < 0:
            errors.append(f"Invalid num_studies: {eb_data['num_studies']}")

    return len(errors) == 0, errors


__all__ = [
    'EVIDENCE_BODY_SCHEMA',
    'get_schema',
    'create_extraction_prompt',
    'validate',
]
