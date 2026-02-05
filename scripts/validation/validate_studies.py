"""
Validate Extracted Studies

Checks study data completeness, PMID resolution rate, and flags
unresolved citations for manual review.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.pipeline.config_loader import load_config
from scripts.pipeline.pipeline_context import PipelineContext
from scripts.extraction.validate_json import validate_with_template
from scripts.extraction.templates import study_template


def run(config_path: str):
    """Run study validation."""
    config = load_config(config_path)
    ctx = PipelineContext(config)

    if not ctx.studies_json.exists():
        print("ERROR: studies.json not found. Run extract_studies.py first.")
        return None

    with open(ctx.studies_json) as f:
        studies = json.load(f)

    print("=" * 60)
    print("STUDY VALIDATION")
    print("=" * 60)

    expected = config.expected_counts.get('studies', 0)
    print(f"\nCount: {len(studies)} extracted, {expected} expected")

    report = validate_with_template(studies, study_template)
    print(f"Valid: {report['valid']}/{report['total_items']}")
    print(f"Validation rate: {report['validation_rate']:.1%}")

    # PMID resolution
    has_pmid = sum(1 for s in studies if s.get('pmid'))
    has_doi = sum(1 for s in studies if s.get('doi'))
    print(f"\nIdentifier resolution:")
    print(f"  PMID: {has_pmid}/{len(studies)} ({has_pmid/len(studies)*100:.0f}%)" if studies else "  No studies")
    print(f"  DOI:  {has_doi}/{len(studies)} ({has_doi/len(studies)*100:.0f}%)" if studies else "")

    # Study type distribution
    types = {}
    for s in studies:
        t = s.get('study_type') or 'Unknown'
        types[t] = types.get(t, 0) + 1
    print(f"\nStudy type distribution: {types}")

    # Year distribution
    years = [s.get('year') for s in studies if s.get('year')]
    if years:
        print(f"Year range: {min(years)}-{max(years)}")

    # Flag unresolved for manual review
    unresolved = [
        {'ref_number': s.get('ref_number'), 'title': s.get('title', '')[:80], 'authors': s.get('authors', '')[:50]}
        for s in studies if not s.get('pmid')
    ]
    if unresolved:
        unresolved_path = ctx.manual_review_dir / "unresolved_pmids.json"
        unresolved_path.parent.mkdir(parents=True, exist_ok=True)
        with open(unresolved_path, 'w') as f:
            json.dump(unresolved, f, indent=2)
        print(f"\n{len(unresolved)} unresolved PMIDs flagged -> {unresolved_path}")

    full_report = {
        **report,
        'expected_count': expected,
        'actual_count': len(studies),
        'pmid_resolved': has_pmid,
        'doi_resolved': has_doi,
        'resolution_rate': has_pmid / len(studies) if studies else 0,
        'study_type_distribution': types,
        'unresolved_count': len(unresolved),
    }
    report_path = ctx.validation_report_path('studies')
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(full_report, f, indent=2)
    print(f"\nFull report saved to {report_path}")

    return full_report


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Validate extracted studies")
    parser.add_argument('--config', required=True, help="Path to guideline YAML config")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
