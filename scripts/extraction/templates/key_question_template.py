"""
Extraction Template: Key Questions

Provides prompt templates and JSON schemas for extracting PICOTS-based
key questions from CPG Appendix A sections.
"""

from typing import Dict, Any, List, Optional


KEY_QUESTION_SCHEMA = {
    "type": "object",
    "required": ["kq_number", "question_text", "population", "intervention", "outcomes_critical"],
    "properties": {
        "kq_number": {
            "type": "integer",
            "description": "Key question number"
        },
        "question_text": {
            "type": "string",
            "description": "Complete key question text"
        },
        "population": {
            "type": "string",
            "description": "PICOTS: Patient population"
        },
        "intervention": {
            "type": "string",
            "description": "PICOTS: Intervention or exposure"
        },
        "comparator": {
            "type": ["string", "null"],
            "description": "PICOTS: Comparator"
        },
        "outcomes_critical": {
            "type": "array",
            "items": {"type": "string"},
            "description": "PICOTS: Critical outcomes (rated 7-9)"
        },
        "outcomes_important": {
            "type": "array",
            "items": {"type": "string"},
            "description": "PICOTS: Important outcomes (rated 4-6)"
        },
        "timing": {
            "type": ["string", "null"],
            "description": "PICOTS: Timing"
        },
        "setting": {
            "type": ["string", "null"],
            "description": "PICOTS: Setting"
        },
        "num_studies": {
            "type": ["integer", "null"],
            "description": "Number of studies addressing this question"
        },
        "topic": {
            "type": "string",
            "description": "Topic area (e.g., Pharmacotherapy, Screening)"
        }
    }
}


def get_schema() -> dict:
    """Return the JSON schema for key question extraction."""
    return KEY_QUESTION_SCHEMA


def create_extraction_prompt(
    section_text: str,
    config: Optional[Any] = None,
) -> str:
    """
    Create extraction prompt for key questions from Appendix A text.

    Args:
        section_text: Markdown or text content of the KQ section
        config: Optional GuidelineConfig

    Returns:
        Formatted prompt string for LLM
    """
    guideline_name = "VA/DoD Clinical Practice Guideline"
    if config:
        guideline_name = config.full_title

    prompt = f"""You are extracting Key Questions (KQs) with PICOTS elements from the {guideline_name}.

INPUT TEXT (from Appendix A / Key Questions section):
{section_text}

TASK: Extract each Key Question as a structured JSON object with complete PICOTS elements.

OUTPUT FORMAT: Return a JSON array of key question objects. Each object must have:
- kq_number: (integer) key question number (e.g., KQ 1 -> 1)
- question_text: (string) complete question text, verbatim
- population: (string) target patient population (P in PICOTS)
- intervention: (string) intervention or exposure being studied (I in PICOTS)
- comparator: (string or null) comparator/control (C in PICOTS)
- outcomes_critical: (array of strings) critical outcomes rated 7-9 on importance scale (O in PICOTS)
- outcomes_important: (array of strings) important but not critical outcomes rated 4-6 (O in PICOTS)
- timing: (string or null) timing/duration considerations (T in PICOTS)
- setting: (string or null) clinical setting (S in PICOTS)
- num_studies: (integer or null) number of studies found for this KQ, if mentioned
- topic: (string) topic area (e.g., "Pharmacotherapy", "Screening", "Self-Management")

CRITICAL RULES:
1. Extract question text VERBATIM
2. Separate critical from important outcomes based on explicit ratings or labels in the text
3. If outcomes are listed without ratings, include all as critical
4. Population should describe the specific patient group, not just "adults"
5. Return ONLY the JSON array, no markdown, no explanation

Example output format:
[
  {{
    "kq_number": 1,
    "question_text": "For adults with prediabetes, does lifestyle intervention compared to...",
    "population": "Adults with prediabetes (HbA1c 5.7-6.4% or fasting glucose 100-125 mg/dL)",
    "intervention": "Structured lifestyle intervention (diet and exercise)",
    "comparator": "Usual care or no intervention",
    "outcomes_critical": ["Progression to T2DM", "HbA1c reduction", "All-cause mortality"],
    "outcomes_important": ["Weight loss", "Quality of life"],
    "timing": "12 months or longer",
    "setting": "Primary care or community",
    "num_studies": 15,
    "topic": "Prediabetes"
  }}
]

Extract the key questions now. Return only valid JSON."""

    return prompt


def validate(kq_data: Dict[str, Any]) -> tuple:
    """
    Validate extracted key question against schema and business rules.

    Args:
        kq_data: Extracted key question dictionary

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    required = ['kq_number', 'question_text', 'population', 'intervention', 'outcomes_critical']
    for f in required:
        if f not in kq_data:
            errors.append(f"Missing required field: {f}")

    if 'question_text' in kq_data and len(str(kq_data['question_text'])) < 20:
        errors.append(f"Question text too short: {len(kq_data['question_text'])} chars")

    if 'outcomes_critical' in kq_data:
        if not isinstance(kq_data['outcomes_critical'], list):
            errors.append("outcomes_critical must be a list")
        elif len(kq_data['outcomes_critical']) == 0:
            errors.append("outcomes_critical must have at least one outcome")

    if 'kq_number' in kq_data:
        if not isinstance(kq_data['kq_number'], int) or kq_data['kq_number'] < 1:
            errors.append(f"Invalid kq_number: {kq_data['kq_number']}")

    return len(errors) == 0, errors


__all__ = [
    'KEY_QUESTION_SCHEMA',
    'get_schema',
    'create_extraction_prompt',
    'validate',
]
