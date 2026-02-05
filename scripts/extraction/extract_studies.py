"""
Extract Studies from CPG References Section

Parses reference citations using LLM, then enriches with PubMed metadata
in a separate step. Handles the full references section (103 studies for
the diabetes CPG).
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
from scripts.extraction.templates.study_template import (
    create_extraction_prompt,
    validate,
)


def load_references_text(ctx: PipelineContext) -> str:
    """Load the references section text."""
    # Try markdown first
    md_path = ctx.section_md_path("references")
    if md_path.exists():
        with open(md_path, 'r', encoding='utf-8') as f:
            return f.read()

    # Direct PDF extraction
    import fitz
    section_cfg = ctx.config.sections.get('references')
    if section_cfg and ctx.pdf_path.exists():
        doc = fitz.open(str(ctx.pdf_path))
        text_parts = []
        for page_num in range(section_cfg.start_page - 1, min(section_cfg.end_page, len(doc))):
            text_parts.append(doc[page_num].get_text("text"))
        doc.close()
        return "\n".join(text_parts)

    raise FileNotFoundError(
        "References section not found. "
        "Run split_sections.py and convert_to_markdown.py first."
    )


def split_references_into_chunks(text: str, chunk_size: int = 20) -> list:
    """
    Split references text into chunks of ~chunk_size references each.

    References are numbered (e.g., "1.", "2.") so we split on these boundaries.
    """
    import re
    # Find reference boundaries
    # Pattern: line starting with a number followed by period
    lines = text.split('\n')
    references = []
    current_ref = []

    for line in lines:
        # Check if this line starts a new reference
        if re.match(r'^\s*\d{1,3}\.\s', line):
            if current_ref:
                references.append('\n'.join(current_ref))
            current_ref = [line]
        else:
            current_ref.append(line)

    if current_ref:
        references.append('\n'.join(current_ref))

    # Group into chunks
    chunks = []
    for i in range(0, len(references), chunk_size):
        chunk = '\n\n'.join(references[i:i + chunk_size])
        chunks.append(chunk)

    return chunks


def process_study_batch(batch_text: list, client, config) -> list:
    """Process a batch of reference text through the LLM."""
    combined_text = "\n\n".join(batch_text)
    prompt = create_extraction_prompt(combined_text, config)
    result = client.extract(prompt, max_tokens=4096)

    if isinstance(result, dict) and 'studies' in result:
        result = result['studies']
    if not isinstance(result, list):
        result = [result]

    return result


def run(config_path: str, resume: bool = True):
    """Run study extraction pipeline."""
    config = load_config(config_path)
    ctx = PipelineContext(config)
    ctx.ensure_directories()

    print("=" * 60)
    print("EXTRACTING STUDIES")
    print("=" * 60)

    print("Loading references section text...")
    references_text = load_references_text(ctx)
    print(f"  Loaded {len(references_text)} characters")

    expected = config.expected_counts.get('studies', '?')
    print(f"  Expected: {expected} studies")

    # Split into processable chunks
    print("Splitting references into chunks...")
    chunks = split_references_into_chunks(references_text, chunk_size=15)
    print(f"  Split into {len(chunks)} chunks")

    # Initialize AI client
    print(f"Initializing {config.extraction.llm_provider} client...")
    client = create_extraction_client(config.extraction.llm_provider, config.extraction.llm_model)

    checkpoint_dir = str(ctx.checkpoint_path("studies"))
    processor = BatchProcessor(
        batch_size=1,  # Each "item" is already a chunk of ~15 references
        checkpoint_dir=checkpoint_dir,
        output_file=str(ctx.studies_json),
        task_name="studies",
    )

    def process_batch(batch):
        return process_study_batch(batch, client, config)

    results, errors = processor.process(chunks, process_batch, resume=resume)

    # Deduplicate by ref_number
    seen = set()
    unique_results = []
    for study in results:
        ref_num = study.get('ref_number')
        if ref_num and ref_num not in seen:
            seen.add(ref_num)
            unique_results.append(study)
        elif ref_num in seen:
            print(f"  WARNING: Duplicate ref_number {ref_num}, keeping first occurrence")

    # Overwrite with deduplicated results
    if len(unique_results) != len(results):
        print(f"  Deduplicated: {len(results)} -> {len(unique_results)} studies")
        results = unique_results
        with open(ctx.studies_json, 'w') as f:
            json.dump(results, f, indent=2)

    # Validate
    print("\nValidating extracted studies...")
    valid_count = 0
    invalid_items = []
    for i, study in enumerate(results):
        is_valid, errs = validate(study)
        if is_valid:
            valid_count += 1
        else:
            invalid_items.append({'index': i, 'ref_number': study.get('ref_number'), 'errors': errs})

    print(f"  Valid: {valid_count}/{len(results)}")
    if invalid_items:
        print(f"  Invalid: {len(invalid_items)}")
        for item in invalid_items[:5]:
            print(f"    Ref {item['ref_number']}: {item['errors']}")

    # Save report
    report = {
        'total_extracted': len(results),
        'valid': valid_count,
        'invalid': len(invalid_items),
        'invalid_items': invalid_items[:20],  # Limit for readability
    }
    report_path = ctx.validation_report_path('studies')
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\nValidation report saved to {report_path}")

    print("\nStudy extraction complete")
    return results


def main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Extract studies from CPG references")
    parser.add_argument('--config', required=True, help="Path to guideline YAML config")
    parser.add_argument('--no-resume', action='store_true', help="Start fresh")
    args = parser.parse_args()
    run(args.config, resume=not args.no_resume)


if __name__ == "__main__":
    main()
