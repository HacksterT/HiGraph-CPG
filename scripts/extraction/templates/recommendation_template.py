"""
Extraction Template: Recommendations

Provides prompt templates and JSON schemas for extracting clinical practice
guideline recommendations. Parameterized by guideline config so the same
template works for any VA/DoD CPG.
"""

from typing import Dict, Any, List, Optional


RECOMMENDATION_SCHEMA = {
    "type": "object",
    "required": ["rec_number", "rec_text", "strength", "direction", "topic", "category"],
    "properties": {
        "rec_number": {
            "type": "integer",
            "description": "Sequential recommendation number"
        },
        "rec_text": {
            "type": "string",
            "description": "Complete recommendation text, verbatim from document"
        },
        "strength": {
            "type": "string",
            "enum": ["Strong", "Weak", "Neither for nor against"],
            "description": "GRADE recommendation strength"
        },
        "direction": {
            "type": "string",
            "enum": ["For", "Against", "Neither"],
            "description": "Recommendation direction"
        },
        "topic": {
            "type": "string",
            "description": "Topic classification from document"
        },
        "subtopic": {
            "type": ["string", "null"],
            "description": "Subtopic classification if present"
        },
        "category": {
            "type": "string",
            "description": "Recommendation category (New-added, Amended, etc.)"
        },
        "page_number": {
            "type": "integer",
            "description": "Page number where recommendation appears"
        }
    }
}


def get_schema() -> dict:
    """Return the JSON schema for recommendation extraction."""
    return RECOMMENDATION_SCHEMA


def create_extraction_prompt(
    table_rows: List[Dict[str, Any]],
    config: Optional[Any] = None,
) -> str:
    """
    Create extraction prompt for a batch of recommendations.

    Args:
        table_rows: List of table row dictionaries from pdfplumber extraction
        config: Optional GuidelineConfig for guideline-specific customization

    Returns:
        Formatted prompt string for LLM
    """
    guideline_name = "VA/DoD Clinical Practice Guideline"
    if config:
        guideline_name = config.full_title

    # Build markdown table from rows
    table_text = "| Topic | Subtopic | # | Recommendation | Strength | Category |\n"
    table_text += "|-------|----------|---|----------------|----------|----------|\n"

    for row in table_rows:
        # Use normalized column names (from config mapping) or raw names
        topic = row.get('topic', '') or row.get('Topic', '') or ''
        subtopic = row.get('subtopic', '') or row.get('Subtopic', '') or ''
        rec_num = row.get('rec_number', '') or row.get('#', '') or ''
        rec_text = row.get('rec_text', '') or row.get('Recommendation', '') or ''
        strength = (row.get('strength_raw', '') or row.get('Strengtha', '')
                    or row.get('Strength', '') or '')
        category = (row.get('category', '') or row.get('Categoryb', '')
                    or row.get('Category', '') or '')

        # Truncate for table display
        display_text = rec_text[:100] + "..." if len(str(rec_text)) > 100 else rec_text
        table_text += f"| {topic} | {subtopic} | {rec_num} | {display_text} | {strength} | {category} |\n"

    prompt = f"""You are extracting clinical practice guideline recommendations from the {guideline_name}.

INPUT DATA (table rows):
{table_text}

TASK: Extract each recommendation as a structured JSON object.

OUTPUT FORMAT: Return a JSON array of recommendation objects. Each object must have:
- rec_number: (integer) from the # column
- rec_text: (string) complete recommendation text, verbatim from Recommendation column
- strength: (string) must be exactly one of: "Strong", "Weak", or "Neither for nor against"
- direction: (string) extract from strength field - must be exactly one of: "For", "Against", or "Neither"
- topic: (string) from Topic column
- subtopic: (string or null) from Subtopic column, null if empty
- category: (string) from Category column
- page_number: (integer) estimate based on table position

CRITICAL RULES:
1. Extract recommendation text VERBATIM - do not summarize or paraphrase
2. Map strength values exactly: "Strong for" -> strength="Strong", direction="For"
3. "Weak against" -> strength="Weak", direction="Against"
4. "Neither for nor against" -> strength="Neither for nor against", direction="Neither"
5. Topic/subtopic exactly as shown in table columns
6. Return ONLY the JSON array, no markdown formatting, no explanation

Example output format:
[
  {{
    "rec_number": 1,
    "rec_text": "In adults with prediabetes, we suggest aerobic exercise...",
    "strength": "Weak",
    "direction": "For",
    "topic": "Prediabetes",
    "subtopic": "Exercise/Nutrition",
    "category": "Reviewed, New-added",
    "page_number": 25
  }}
]

Extract the recommendations now. Return only valid JSON."""

    return prompt


def parse_strength_direction(strength_text: str) -> tuple:
    """
    Parse combined strength text into separate strength and direction.

    Args:
        strength_text: Text like "Strong for", "Weak against", "Neither for nor against"

    Returns:
        Tuple of (strength, direction)
    """
    text_lower = strength_text.lower().strip()

    if 'strong' in text_lower:
        strength = 'Strong'
    elif 'weak' in text_lower:
        strength = 'Weak'
    elif 'neither' in text_lower:
        strength = 'Neither for nor against'
    else:
        strength = 'Unknown'

    if 'neither' in text_lower:
        direction = 'Neither'
    elif 'against' in text_lower:
        direction = 'Against'
    elif 'for' in text_lower:
        direction = 'For'
    else:
        direction = 'Unknown'

    return strength, direction


def validate(rec_data: Dict[str, Any]) -> tuple:
    """
    Validate extracted recommendation against schema and business rules.

    Args:
        rec_data: Extracted recommendation dictionary

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    required = ['rec_number', 'rec_text', 'strength', 'direction', 'topic', 'category']
    for f in required:
        if f not in rec_data:
            errors.append(f"Missing required field: {f}")

    valid_strengths = ['Strong', 'Weak', 'Neither for nor against']
    if 'strength' in rec_data and rec_data['strength'] not in valid_strengths:
        errors.append(f"Invalid strength: {rec_data['strength']}. Must be one of {valid_strengths}")

    valid_directions = ['For', 'Against', 'Neither']
    if 'direction' in rec_data and rec_data['direction'] not in valid_directions:
        errors.append(f"Invalid direction: {rec_data['direction']}. Must be one of {valid_directions}")

    if 'rec_text' in rec_data and len(str(rec_data['rec_text'])) < 20:
        errors.append(f"Recommendation text too short: {len(rec_data['rec_text'])} chars")

    return len(errors) == 0, errors


# Backward compatibility aliases
validate_recommendation = validate

__all__ = [
    'RECOMMENDATION_SCHEMA',
    'get_schema',
    'create_extraction_prompt',
    'parse_strength_direction',
    'validate',
    'validate_recommendation',
]
