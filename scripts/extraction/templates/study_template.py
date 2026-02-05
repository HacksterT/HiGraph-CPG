"""
Extraction Template: Studies

Provides prompt templates and JSON schemas for extracting study citations
from CPG reference sections. The LLM parses citation text into structured
fields; PubMed enrichment happens in a separate step.
"""

from typing import Dict, Any, List, Optional


STUDY_SCHEMA = {
    "type": "object",
    "required": ["ref_number", "title", "authors", "year"],
    "properties": {
        "ref_number": {
            "type": "integer",
            "description": "Reference number from the document"
        },
        "title": {
            "type": "string",
            "description": "Study title"
        },
        "authors": {
            "type": "string",
            "description": "Author list (first author et al. or full list)"
        },
        "journal": {
            "type": ["string", "null"],
            "description": "Journal name"
        },
        "year": {
            "type": "integer",
            "description": "Publication year"
        },
        "volume": {
            "type": ["string", "null"],
            "description": "Journal volume"
        },
        "pages": {
            "type": ["string", "null"],
            "description": "Page range"
        },
        "doi": {
            "type": ["string", "null"],
            "description": "DOI if present in citation"
        },
        "pmid": {
            "type": ["string", "null"],
            "description": "PubMed ID if present in citation"
        },
        "study_type": {
            "type": ["string", "null"],
            "enum": ["RCT", "Systematic Review", "Meta-analysis", "Cohort",
                     "Cross-sectional", "Case-control", "Guideline", "Other", None],
            "description": "Study type if identifiable from title/context"
        },
        "citation_text": {
            "type": "string",
            "description": "Original citation text, verbatim"
        }
    }
}


def get_schema() -> dict:
    """Return the JSON schema for study extraction."""
    return STUDY_SCHEMA


def create_extraction_prompt(
    references_text: str,
    config: Optional[Any] = None,
) -> str:
    """
    Create extraction prompt for parsing reference citations.

    Args:
        references_text: Text of the references section (batch of citations)
        config: Optional GuidelineConfig

    Returns:
        Formatted prompt string for LLM
    """
    guideline_name = "VA/DoD Clinical Practice Guideline"
    if config:
        guideline_name = config.full_title

    prompt = f"""You are parsing reference citations from the {guideline_name}.

INPUT TEXT (references section):
{references_text}

TASK: Parse each numbered reference into a structured JSON object.

OUTPUT FORMAT: Return a JSON array of study objects. Each object must have:
- ref_number: (integer) reference number as it appears in the document
- title: (string) study/article title
- authors: (string) author list
- journal: (string or null) journal name
- year: (integer) publication year
- volume: (string or null) volume number
- pages: (string or null) page range
- doi: (string or null) DOI if present
- pmid: (string or null) PubMed ID if present
- study_type: (string or null) one of: "RCT", "Systematic Review", "Meta-analysis", "Cohort", "Cross-sectional", "Case-control", "Guideline", "Other"
- citation_text: (string) the original citation text, verbatim

CRITICAL RULES:
1. Parse each numbered reference (e.g., "1.", "2.") as a separate entry
2. Extract the title accurately - it usually appears after author names and before journal
3. Year is typically a 4-digit number near the end of the citation or after the journal name
4. Infer study_type from title keywords: "randomized" -> RCT, "systematic review" or "meta-analysis", "cohort", etc.
5. If you can't determine study_type, set it to null
6. Preserve the complete citation_text verbatim
7. Return ONLY the JSON array, no markdown, no explanation

Example output format:
[
  {{
    "ref_number": 1,
    "title": "Effect of intensive blood-glucose control with metformin on complications in overweight patients with type 2 diabetes",
    "authors": "UK Prospective Diabetes Study Group",
    "journal": "Lancet",
    "year": 1998,
    "volume": "352",
    "pages": "854-865",
    "doi": null,
    "pmid": null,
    "study_type": "RCT",
    "citation_text": "1. UK Prospective Diabetes Study Group. Effect of intensive blood-glucose control with metformin..."
  }}
]

Parse the references now. Return only valid JSON."""

    return prompt


def validate(study_data: Dict[str, Any]) -> tuple:
    """
    Validate extracted study against schema and business rules.

    Args:
        study_data: Extracted study dictionary

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    required = ['ref_number', 'title', 'authors', 'year']
    for f in required:
        if f not in study_data:
            errors.append(f"Missing required field: {f}")

    if 'title' in study_data and len(str(study_data['title'])) < 10:
        errors.append(f"Title too short: {len(study_data['title'])} chars")

    if 'year' in study_data:
        year = study_data['year']
        if not isinstance(year, int) or year < 1900 or year > 2030:
            errors.append(f"Invalid year: {year}")

    if 'ref_number' in study_data:
        if not isinstance(study_data['ref_number'], int) or study_data['ref_number'] < 1:
            errors.append(f"Invalid ref_number: {study_data['ref_number']}")

    valid_types = ['RCT', 'Systematic Review', 'Meta-analysis', 'Cohort',
                   'Cross-sectional', 'Case-control', 'Guideline', 'Other', None]
    if 'study_type' in study_data and study_data['study_type'] not in valid_types:
        errors.append(f"Invalid study_type: {study_data['study_type']}")

    return len(errors) == 0, errors


__all__ = [
    'STUDY_SCHEMA',
    'get_schema',
    'create_extraction_prompt',
    'validate',
]
