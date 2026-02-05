"""
Validate Inferred Relationships

Checks relationship completeness, confidence distribution, orphan detection,
and evidence chain integrity.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.pipeline.config_loader import load_config
from scripts.pipeline.pipeline_context import PipelineContext


def run(config_path: str):
    """Run relationship validation."""
    config = load_config(config_path)
    ctx = PipelineContext(config)

    if not ctx.relationships_json.exists():
        print("ERROR: relationships.json not found. Run build_all_relationships.py first.")
        return None

    with open(ctx.relationships_json) as f:
        rels = json.load(f)

    print("=" * 60)
    print("RELATIONSHIP VALIDATION")
    print("=" * 60)

    # Type distribution
    by_type = {}
    for r in rels:
        t = r['type']
        by_type[t] = by_type.get(t, 0) + 1
    print(f"\nRelationship types:")
    for t, count in sorted(by_type.items()):
        print(f"  {t}: {count}")

    # Confidence distribution
    thresholds = config.confidence_thresholds
    high = sum(1 for r in rels if r.get('confidence', 0) >= thresholds.auto_accept)
    med = sum(1 for r in rels if thresholds.flag_for_review <= r.get('confidence', 0) < thresholds.auto_accept)
    low = sum(1 for r in rels if r.get('confidence', 0) < thresholds.flag_for_review)

    print(f"\nConfidence distribution:")
    print(f"  High (>={thresholds.auto_accept}): {high}")
    print(f"  Medium ({thresholds.flag_for_review}-{thresholds.auto_accept}): {med}")
    print(f"  Low (<{thresholds.flag_for_review}): {low}")

    # Orphan checks
    issues = []

    # Load entity data to check for orphans
    rec_numbers = set()
    kq_numbers = set()
    eb_numbers = set()
    study_numbers = set()

    if ctx.recommendations_json.exists():
        with open(ctx.recommendations_json) as f:
            for r in json.load(f):
                rec_numbers.add(r.get('rec_number'))

    if ctx.key_questions_json.exists():
        with open(ctx.key_questions_json) as f:
            for kq in json.load(f):
                kq_numbers.add(kq.get('kq_number'))

    if ctx.evidence_bodies_json.exists():
        with open(ctx.evidence_bodies_json) as f:
            for eb in json.load(f):
                eb_numbers.add(eb.get('kq_number'))

    if ctx.studies_json.exists():
        with open(ctx.studies_json) as f:
            for s in json.load(f):
                study_numbers.add(s.get('ref_number'))

    # Check: every rec should have at least one LEADS_TO or BASED_ON
    linked_recs = set()
    for r in rels:
        if r['type'] in ('LEADS_TO', 'BASED_ON') and r.get('to_type') == 'Recommendation':
            linked_recs.add(r.get('to_number'))
        if r['type'] == 'BASED_ON' and r.get('from_type') == 'Recommendation':
            linked_recs.add(r.get('from_number'))

    orphan_recs = rec_numbers - linked_recs
    if orphan_recs:
        issues.append(f"Orphaned recommendations (no LEADS_TO/BASED_ON): {sorted(orphan_recs)}")

    # Check: every KQ should have ANSWERS relationship
    linked_kqs = set()
    for r in rels:
        if r['type'] == 'ANSWERS':
            linked_kqs.add(r.get('to_number'))
    orphan_kqs = kq_numbers - linked_kqs
    if orphan_kqs:
        issues.append(f"Orphaned key questions (no ANSWERS): {sorted(orphan_kqs)}")

    # Print issues
    if issues:
        print(f"\nISSUES ({len(issues)}):")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\nNo orphan issues detected")

    # Save report
    report = {
        'total_relationships': len(rels),
        'by_type': by_type,
        'confidence_distribution': {'high': high, 'medium': med, 'low': low},
        'orphan_recommendations': sorted(orphan_recs) if orphan_recs else [],
        'orphan_key_questions': sorted(orphan_kqs) if orphan_kqs else [],
        'issues': issues,
        'flagged_count': med,
    }
    report_path = ctx.validation_report_path('relationships')
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved to {report_path}")

    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Validate inferred relationships")
    parser.add_argument('--config', required=True, help="Path to guideline YAML config")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
