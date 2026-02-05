"""
Extract Recommendations from CPG Table 5

Uses the recommendation template + batch processor + AI client to extract
all recommendations from the pre-extracted table data. Saves checkpoints
after each batch and produces validated output.
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
from scripts.extraction.templates.recommendation_template import (
    create_extraction_prompt,
    parse_strength_direction,
    validate,
)


def load_table_data(ctx: PipelineContext) -> list:
    """Load recommendation table rows from preprocessed data."""
    table_path = ctx.table_path("table_5_recommendations")

    if not table_path.exists():
        # Try combined tables file
        combined = ctx.preprocessed_dir / "tables.json"
        if combined.exists():
            with open(combined) as f:
                tables = json.load(f)
            if 'table_5_recommendations' in tables:
                return tables['table_5_recommendations']['data']

        raise FileNotFoundError(
            f"Table data not found at {table_path}. "
            "Run extract_tables.py first."
        )

    with open(table_path) as f:
        table_data = json.load(f)

    return table_data['data']


def process_recommendation_batch(batch: list, client, config) -> list:
    """Process a batch of table rows through the LLM."""
    prompt = create_extraction_prompt(batch, config)
    result = client.extract(prompt)

    # Result should be a list of recommendation dicts
    if isinstance(result, dict) and 'recommendations' in result:
        result = result['recommendations']
    if not isinstance(result, list):
        result = [result]

    # Post-process: fix strength/direction if needed
    for rec in result:
        if 'strength_raw' in rec and ('strength' not in rec or 'direction' not in rec):
            strength, direction = parse_strength_direction(rec['strength_raw'])
            rec['strength'] = strength
            rec['direction'] = direction

    return result


def run(config_path: str, resume: bool = True):
    """
    Run recommendation extraction pipeline.

    Args:
        config_path: Path to guideline YAML config
        resume: Whether to resume from checkpoints
    """
    config = load_config(config_path)
    ctx = PipelineContext(config)
    ctx.ensure_directories()

    print("=" * 60)
    print("EXTRACTING RECOMMENDATIONS")
    print("=" * 60)

    # Load table data
    print("Loading table data...")
    rows = load_table_data(ctx)
    print(f"  Found {len(rows)} table rows")

    expected = config.expected_counts.get('recommendations', '?')
    print(f"  Expected: {expected} recommendations")

    # Initialize AI client
    print(f"Initializing {config.extraction.llm_provider} client...")
    client = create_extraction_client(config.extraction.llm_provider, config.extraction.llm_model)

    # Create processor
    checkpoint_dir = str(ctx.checkpoint_path("recommendations"))
    processor = BatchProcessor(
        batch_size=config.extraction.batch_size,
        checkpoint_dir=checkpoint_dir,
        output_file=str(ctx.recommendations_json),
        task_name="recommendations",
    )

    # Process
    def process_batch(batch):
        return process_recommendation_batch(batch, client, config)

    results, errors = processor.process(rows, process_batch, resume=resume)

    # Validate results
    print("\nValidating extracted recommendations...")
    valid_count = 0
    invalid_items = []
    for i, rec in enumerate(results):
        is_valid, errs = validate(rec)
        if is_valid:
            valid_count += 1
        else:
            invalid_items.append({'index': i, 'rec_number': rec.get('rec_number'), 'errors': errs})

    print(f"  Valid: {valid_count}/{len(results)}")
    if invalid_items:
        print(f"  Invalid: {len(invalid_items)}")
        for item in invalid_items[:5]:
            print(f"    Rec {item['rec_number']}: {item['errors']}")

    # Save validation report
    report = {
        'total_extracted': len(results),
        'valid': valid_count,
        'invalid': len(invalid_items),
        'batch_errors': len(errors),
        'invalid_items': invalid_items,
    }
    report_path = ctx.validation_report_path('recommendations')
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\nValidation report saved to {report_path}")

    print("\nRecommendation extraction complete")
    return results


def main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Extract recommendations from CPG")
    parser.add_argument('--config', required=True, help="Path to guideline YAML config")
    parser.add_argument('--no-resume', action='store_true', help="Start fresh, ignore checkpoints")
    args = parser.parse_args()
    run(args.config, resume=not args.no_resume)


if __name__ == "__main__":
    main()
