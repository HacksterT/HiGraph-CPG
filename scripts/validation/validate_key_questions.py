"""
Validate Extracted Key Questions

Checks all 12 key questions for PICOTS completeness and accuracy.
100% review since the set is small.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.pipeline.config_loader import load_config
from scripts.pipeline.pipeline_context import PipelineContext
from scripts.extraction.validate_json import validate_with_template
from scripts.extraction.templates import key_question_template


def run(config_path: str):
    """Run key question validation."""
    config = load_config(config_path)
    ctx = PipelineContext(config)

    if not ctx.key_questions_json.exists():
        print("ERROR: key_questions.json not found. Run extract_key_questions.py first.")
        return None

    with open(ctx.key_questions_json) as f:
        kqs = json.load(f)

    print("=" * 60)
    print("KEY QUESTION VALIDATION")
    print("=" * 60)

    expected = config.expected_counts.get('key_questions', 0)
    print(f"\nCount: {len(kqs)} extracted, {expected} expected")

    report = validate_with_template(kqs, key_question_template)
    print(f"Valid: {report['valid']}/{report['total_items']}")
    print(f"Validation rate: {report['validation_rate']:.1%}")

    # PICOTS completeness check
    picots_fields = ['population', 'intervention', 'comparator', 'outcomes_critical', 'timing', 'setting']
    completeness = {field: 0 for field in picots_fields}
    for kq in kqs:
        for field in picots_fields:
            val = kq.get(field)
            if val and val != "null" and val != []:
                completeness[field] += 1

    print(f"\nPICOTS completeness ({len(kqs)} KQs):")
    for field, count in completeness.items():
        pct = count / len(kqs) * 100 if kqs else 0
        print(f"  {field}: {count}/{len(kqs)} ({pct:.0f}%)")

    # Full review (all 12)
    print(f"\nFull review of all {len(kqs)} key questions:")
    for kq in kqs:
        print(f"\n  KQ {kq.get('kq_number')}:")
        print(f"    Topic: {kq.get('topic')}")
        q_text = str(kq.get('question_text', ''))
        print(f"    Question: {q_text[:150]}{'...' if len(q_text) > 150 else ''}")
        print(f"    Population: {kq.get('population')}")
        print(f"    Intervention: {kq.get('intervention')}")
        print(f"    Outcomes (critical): {kq.get('outcomes_critical')}")

    full_report = {
        **report,
        'expected_count': expected,
        'actual_count': len(kqs),
        'picots_completeness': completeness,
    }
    report_path = ctx.validation_report_path('key_questions')
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(full_report, f, indent=2)
    print(f"\nFull report saved to {report_path}")

    return full_report


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Validate extracted key questions")
    parser.add_argument('--config', required=True, help="Path to guideline YAML config")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
