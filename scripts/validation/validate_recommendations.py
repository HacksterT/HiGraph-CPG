"""
Validate Extracted Recommendations

Checks recommendations against schema, business rules, and expected counts.
Samples random items for manual review.
"""

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.pipeline.config_loader import load_config
from scripts.pipeline.pipeline_context import PipelineContext
from scripts.extraction.templates.recommendation_template import validate, get_schema
from scripts.extraction.validate_json import validate_with_template
from scripts.extraction.templates import recommendation_template


def run(config_path: str, sample_size: int = 10):
    """Run recommendation validation."""
    config = load_config(config_path)
    ctx = PipelineContext(config)

    if not ctx.recommendations_json.exists():
        print("ERROR: recommendations.json not found. Run extract_recommendations.py first.")
        return None

    with open(ctx.recommendations_json) as f:
        recs = json.load(f)

    print("=" * 60)
    print("RECOMMENDATION VALIDATION")
    print("=" * 60)

    # Count check
    expected = config.expected_counts.get('recommendations', 0)
    print(f"\nCount: {len(recs)} extracted, {expected} expected")
    if len(recs) != expected:
        print(f"  WARNING: Count mismatch ({len(recs)} vs {expected})")

    # Schema + business rule validation
    report = validate_with_template(recs, recommendation_template)
    print(f"Valid: {report['valid']}/{report['total_items']}")
    print(f"Validation rate: {report['validation_rate']:.1%}")

    # Check for duplicate rec_numbers
    rec_numbers = [r.get('rec_number') for r in recs if r.get('rec_number')]
    duplicates = [n for n in rec_numbers if rec_numbers.count(n) > 1]
    if duplicates:
        print(f"\nDuplicate rec_numbers: {set(duplicates)}")

    # Check strength/direction distribution
    strengths = {}
    directions = {}
    for rec in recs:
        s = rec.get('strength', 'Unknown')
        d = rec.get('direction', 'Unknown')
        strengths[s] = strengths.get(s, 0) + 1
        directions[d] = directions.get(d, 0) + 1

    print(f"\nStrength distribution: {strengths}")
    print(f"Direction distribution: {directions}")

    # Random sample for manual review
    sample = random.sample(recs, min(sample_size, len(recs)))
    print(f"\nRandom sample ({len(sample)} items) for manual review:")
    for rec in sample:
        print(f"\n  Rec #{rec.get('rec_number')}:")
        print(f"    Topic: {rec.get('topic')}")
        print(f"    Strength: {rec.get('strength')} {rec.get('direction')}")
        text = str(rec.get('rec_text', ''))
        print(f"    Text: {text[:120]}{'...' if len(text) > 120 else ''}")

    # Save report
    full_report = {
        **report,
        'expected_count': expected,
        'actual_count': len(recs),
        'count_match': len(recs) == expected,
        'duplicates': list(set(duplicates)),
        'strength_distribution': strengths,
        'direction_distribution': directions,
        'sample_rec_numbers': [r.get('rec_number') for r in sample],
    }
    report_path = ctx.validation_report_path('recommendations')
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(full_report, f, indent=2)
    print(f"\nFull report saved to {report_path}")

    return full_report


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Validate extracted recommendations")
    parser.add_argument('--config', required=True, help="Path to guideline YAML config")
    parser.add_argument('--sample-size', type=int, default=10, help="Number of items to sample")
    args = parser.parse_args()
    run(args.config, sample_size=args.sample_size)


if __name__ == "__main__":
    main()
