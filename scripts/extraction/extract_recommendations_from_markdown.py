"""
Extract Recommendations from Markdown (fallback when table extraction fails)

Uses the markdown file directly instead of the pdfplumber table JSON.
"""

import json
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

load_dotenv()

from scripts.pipeline.config_loader import load_config
from scripts.pipeline.pipeline_context import PipelineContext
from scripts.extraction.ai_client import AIExtractionClient
from scripts.extraction.templates.recommendation_template import (
    parse_strength_direction,
    validate,
)


def create_markdown_extraction_prompt(markdown_text: str, config) -> str:
    """Create extraction prompt using markdown text directly."""
    guideline_name = config.full_title if config else "VA/DoD Clinical Practice Guideline"

    prompt = f"""You are extracting clinical practice guideline recommendations from the {guideline_name}.

INPUT: Below is the markdown text from the recommendations section (Table 5 and detailed discussions).
Extract ALL recommendations numbered 1 through 26.

---
{markdown_text}
---

TASK: Extract each recommendation as a structured JSON object.

OUTPUT FORMAT: Return a JSON object with a "recommendations" key containing an array. Each recommendation object must have:
- rec_number: (integer) the recommendation number (1-26)
- rec_text: (string) complete recommendation text, verbatim from the document
- strength: (string) exactly one of: "Strong", "Weak", or "Neither for nor against"
- direction: (string) exactly one of: "For", "Against", or "Neither"
- topic: (string) the Topic classification (e.g., "Prediabetes", "Management of Type 2 Diabetes Mellitus")
- subtopic: (string or null) the Subtopic classification (e.g., "Exercise/Nutrition", "Glycemic Management"), null if none
- category: (string) the Category (e.g., "Reviewed, New-added", "Not Reviewed, Amended")
- page_number: (integer or null) page number if visible in the text

CRITICAL RULES:
1. Extract the COMPLETE recommendation text verbatim - do not summarize
2. Parse strength/direction from formats like:
   - "Weak for" -> strength="Weak", direction="For"
   - "Strong for" -> strength="Strong", direction="For"
   - "Weak against" -> strength="Weak", direction="Against"
   - "Neither for nor against" -> strength="Neither for nor against", direction="Neither"
3. Include ALL 26 recommendations - do not skip any
4. Return ONLY valid JSON, no markdown code blocks, no explanation

Example output:
{{"recommendations": [
  {{"rec_number": 1, "rec_text": "In adults with prediabetes, we suggest aerobic exercise...", "strength": "Weak", "direction": "For", "topic": "Prediabetes", "subtopic": "Exercise/Nutrition", "category": "Reviewed, New-added", "page_number": 24}},
  {{"rec_number": 2, "rec_text": "...", ...}}
]}}

Extract all 26 recommendations now. Return only valid JSON."""

    return prompt


def run(config_path: str):
    """Run recommendation extraction from markdown."""
    config = load_config(config_path)
    ctx = PipelineContext(config)
    ctx.ensure_directories()

    print("=" * 60)
    print("EXTRACTING RECOMMENDATIONS FROM MARKDOWN")
    print("=" * 60)

    # Load markdown
    md_path = ctx.preprocessed_dir / "sections" / "recommendations_table.md"
    if not md_path.exists():
        raise FileNotFoundError(f"Markdown not found: {md_path}")

    markdown_text = md_path.read_text(encoding='utf-8')
    print(f"Loaded markdown: {len(markdown_text)} chars from {md_path}")

    # Truncate if too long (GPT-4 context limit)
    max_chars = 100000  # ~25k tokens
    if len(markdown_text) > max_chars:
        markdown_text = markdown_text[:max_chars]
        print(f"  Truncated to {max_chars} chars")

    # Initialize AI client
    provider = config.extraction.llm_provider
    model = config.extraction.llm_model
    print(f"Initializing {provider} client with model {model}...")

    client = AIExtractionClient(provider=provider, model=model)

    # Create prompt and extract
    print("Sending extraction request...")
    prompt = create_markdown_extraction_prompt(markdown_text, config)

    result = client.extract(prompt, max_tokens=4096)

    # Parse result
    if isinstance(result, dict) and 'recommendations' in result:
        recommendations = result['recommendations']
    elif isinstance(result, list):
        recommendations = result
    else:
        print(f"Unexpected result format: {type(result)}")
        recommendations = []

    print(f"\nExtracted {len(recommendations)} recommendations")

    # Post-process: fix strength/direction if needed
    for rec in recommendations:
        if 'strength_raw' in rec:
            strength, direction = parse_strength_direction(rec['strength_raw'])
            rec['strength'] = strength
            rec['direction'] = direction

    # Validate
    print("\nValidating...")
    valid_count = 0
    invalid_items = []
    for i, rec in enumerate(recommendations):
        is_valid, errs = validate(rec)
        if is_valid:
            valid_count += 1
        else:
            invalid_items.append({'index': i, 'rec_number': rec.get('rec_number'), 'errors': errs})

    print(f"  Valid: {valid_count}/{len(recommendations)}")
    if invalid_items:
        print(f"  Invalid: {len(invalid_items)}")
        for item in invalid_items[:5]:
            print(f"    Rec {item['rec_number']}: {item['errors']}")

    # Save results
    output_path = ctx.recommendations_json
    with open(output_path, 'w') as f:
        json.dump(recommendations, f, indent=2)
    print(f"\nSaved to {output_path}")

    # Save validation report
    report = {
        'total_extracted': len(recommendations),
        'valid': valid_count,
        'invalid': len(invalid_items),
        'invalid_items': invalid_items,
    }
    report_path = ctx.validation_report_path('recommendations')
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"Validation report saved to {report_path}")

    return recommendations


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True, help='Path to guideline config YAML')
    args = parser.parse_args()

    run(args.config)
