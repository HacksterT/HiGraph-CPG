"""
Extract Evidence Bodies from CPG Appendix A

Extracts evidence synthesis and GRADE quality ratings for each Key Question.
One evidence body per KQ — 12 total for the diabetes CPG.
"""

import json
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

load_dotenv()

from scripts.pipeline.config_loader import load_config
from scripts.pipeline.pipeline_context import PipelineContext
from scripts.extraction.ai_client import create_extraction_client
from scripts.extraction.batch_processor import BatchProcessor
from scripts.extraction.templates.evidence_body_template import (
    create_extraction_prompt,
    validate,
)


def load_evidence_text(ctx: PipelineContext) -> str:
    """Load the evidence synthesis section text."""
    # Try markdown from key_questions_picots section (evidence is embedded within)
    md_path = ctx.section_md_path("key_questions_picots")
    if md_path.exists():
        with open(md_path, 'r', encoding='utf-8') as f:
            return f.read()

    # Try evidence tables section
    md_path = ctx.section_md_path("evidence_tables")
    if md_path.exists():
        with open(md_path, 'r', encoding='utf-8') as f:
            return f.read()

    # Direct PDF extraction
    import fitz
    text_parts = []
    for section_name in ['key_questions_picots', 'evidence_tables']:
        section_cfg = ctx.config.sections.get(section_name)
        if section_cfg and ctx.pdf_path.exists():
            doc = fitz.open(str(ctx.pdf_path))
            for page_num in range(section_cfg.start_page - 1, min(section_cfg.end_page, len(doc))):
                text_parts.append(doc[page_num].get_text("text"))
            doc.close()

    if text_parts:
        return "\n".join(text_parts)

    raise FileNotFoundError(
        "Evidence section text not found. "
        "Run split_sections.py and convert_to_markdown.py first."
    )


def process_evidence_batch(batch_text: list, client, config) -> list:
    """Process evidence text through the LLM."""
    combined_text = "\n\n".join(batch_text)
    prompt = create_extraction_prompt(combined_text, config)
    result = client.extract(prompt, max_tokens=8192)

    if isinstance(result, dict) and 'evidence_bodies' in result:
        result = result['evidence_bodies']
    if not isinstance(result, list):
        result = [result]

    return result


def run(config_path: str, resume: bool = True):
    """Run evidence body extraction pipeline."""
    config = load_config(config_path)
    ctx = PipelineContext(config)
    ctx.ensure_directories()

    print("=" * 60)
    print("EXTRACTING EVIDENCE BODIES")
    print("=" * 60)

    print("Loading evidence section text...")
    section_text = load_evidence_text(ctx)
    print(f"  Loaded {len(section_text)} characters")

    expected = config.expected_counts.get('evidence_bodies', '?')
    print(f"  Expected: {expected} evidence bodies")

    # Initialize AI client
    print(f"Initializing {config.extraction.llm_provider} client...")
    client = create_extraction_client(config.extraction.llm_provider)

    # Process as single batch (small set)
    text_chunks = [section_text]

    checkpoint_dir = str(ctx.checkpoint_path("evidence_bodies"))
    processor = BatchProcessor(
        batch_size=1,
        checkpoint_dir=checkpoint_dir,
        output_file=str(ctx.evidence_bodies_json),
        task_name="evidence_bodies",
    )

    def process_batch(batch):
        return process_evidence_batch(batch, client, config)

    results, errors = processor.process(text_chunks, process_batch, resume=resume)

    # Validate
    print("\nValidating extracted evidence bodies...")
    valid_count = 0
    invalid_items = []
    for i, eb in enumerate(results):
        is_valid, errs = validate(eb)
        if is_valid:
            valid_count += 1
        else:
            invalid_items.append({'index': i, 'kq_number': eb.get('kq_number'), 'errors': errs})

    print(f"  Valid: {valid_count}/{len(results)}")
    if invalid_items:
        print(f"  Invalid: {len(invalid_items)}")
        for item in invalid_items:
            print(f"    KQ {item['kq_number']}: {item['errors']}")

    # Save report
    report = {
        'total_extracted': len(results),
        'valid': valid_count,
        'invalid': len(invalid_items),
        'invalid_items': invalid_items,
    }
    report_path = ctx.validation_report_path('evidence_bodies')
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\nValidation report saved to {report_path}")

    print("\nEvidence body extraction complete")
    return results


def main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Extract evidence bodies from CPG")
    parser.add_argument('--config', required=True, help="Path to guideline YAML config")
    parser.add_argument('--no-resume', action='store_true', help="Start fresh")
    args = parser.parse_args()
    run(args.config, resume=not args.no_resume)


if __name__ == "__main__":
    main()
