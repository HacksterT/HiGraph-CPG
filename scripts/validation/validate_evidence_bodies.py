"""
Validate Extracted Evidence Bodies

Checks evidence body completeness, GRADE ratings, and KQ linkage.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.pipeline.config_loader import load_config
from scripts.pipeline.pipeline_context import PipelineContext
from scripts.extraction.validate_json import validate_with_template
from scripts.extraction.templates import evidence_body_template


def run(config_path: str):
    """Run evidence body validation."""
    config = load_config(config_path)
    ctx = PipelineContext(config)

    if not ctx.evidence_bodies_json.exists():
        print("ERROR: evidence_bodies.json not found. Run extract_evidence_bodies.py first.")
        return None

    with open(ctx.evidence_bodies_json) as f:
        ebs = json.load(f)

    print("=" * 60)
    print("EVIDENCE BODY VALIDATION")
    print("=" * 60)

    expected = config.expected_counts.get('evidence_bodies', 0)
    print(f"\nCount: {len(ebs)} extracted, {expected} expected")

    report = validate_with_template(ebs, evidence_body_template)
    print(f"Valid: {report['valid']}/{report['total_items']}")
    print(f"Validation rate: {report['validation_rate']:.1%}")

    # GRADE distribution
    grades = {}
    for eb in ebs:
        g = eb.get('quality_rating', 'Unknown')
        grades[g] = grades.get(g, 0) + 1
    print(f"\nGRADE distribution: {grades}")

    # KQ coverage check
    kq_numbers = {eb.get('kq_number') for eb in ebs if eb.get('kq_number')}
    expected_kqs = set(range(1, expected + 1))
    missing_kqs = expected_kqs - kq_numbers
    if missing_kqs:
        print(f"\nMissing evidence for KQs: {sorted(missing_kqs)}")
    else:
        print(f"\nAll {len(kq_numbers)} KQs have evidence bodies")

    # Full review
    print(f"\nEvidence body details:")
    for eb in ebs:
        print(f"\n  KQ {eb.get('kq_number')}:")
        print(f"    Topic: {eb.get('topic')}")
        print(f"    GRADE: {eb.get('quality_rating')}")
        print(f"    Studies: {eb.get('num_studies')}")
        findings = str(eb.get('key_findings', ''))
        print(f"    Findings: {findings[:120]}{'...' if len(findings) > 120 else ''}")

    full_report = {
        **report,
        'expected_count': expected,
        'actual_count': len(ebs),
        'grade_distribution': grades,
        'kq_coverage': list(kq_numbers),
        'missing_kqs': list(missing_kqs) if missing_kqs else [],
    }
    report_path = ctx.validation_report_path('evidence_bodies')
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(full_report, f, indent=2)
    print(f"\nFull report saved to {report_path}")

    return full_report


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Validate extracted evidence bodies")
    parser.add_argument('--config', required=True, help="Path to guideline YAML config")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
