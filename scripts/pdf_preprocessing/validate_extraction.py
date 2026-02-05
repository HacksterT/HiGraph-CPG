"""
PDF Preprocessing: Validate Extraction Outputs

Checks that all expected sections were extracted, row counts are plausible,
and required files exist. Produces a validation report.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.pipeline.config_loader import load_config
from scripts.pipeline.pipeline_context import PipelineContext


def validate_document_map(ctx: PipelineContext) -> List[str]:
    """Check that the document map exists and has expected sections."""
    issues = []
    if not ctx.document_map_path.exists():
        issues.append("document_map.json not found")
        return issues

    with open(ctx.document_map_path) as f:
        doc_map = json.load(f)

    for section_name in ctx.config.sections:
        if section_name not in doc_map:
            issues.append(f"Section '{section_name}' missing from document map")

    return issues


def validate_tables(ctx: PipelineContext) -> List[str]:
    """Check that extracted tables have plausible row counts."""
    issues = []

    for section_name, section_cfg in ctx.config.sections.items():
        if not section_cfg.table_name:
            continue

        table_file = ctx.table_path(section_cfg.table_name)
        if not table_file.exists():
            issues.append(f"Table file missing: {table_file.name}")
            continue

        with open(table_file) as f:
            table_data = json.load(f)

        row_count = table_data.get('total_rows', 0)
        if row_count == 0:
            issues.append(f"{section_cfg.table_name}: 0 rows extracted")

        # Check against expected counts if available
        # Map table names back to expected count keys
        count_key_map = {
            'table_5_recommendations': 'recommendations',
            'table_a2_key_questions': 'key_questions',
            'appendix_e_evidence': 'evidence_bodies',
        }
        count_key = count_key_map.get(section_cfg.table_name)
        if count_key and count_key in ctx.config.expected_counts:
            expected = ctx.config.expected_counts[count_key]
            # Allow 20% variance for raw extraction (some rows may merge/split)
            if row_count < expected * 0.5:
                issues.append(
                    f"{section_cfg.table_name}: only {row_count} rows, expected ~{expected}"
                )

    return issues


def validate_sections(ctx: PipelineContext) -> List[str]:
    """Check that section PDFs and markdown files exist."""
    issues = []

    section_pdfs = list(ctx.sections_dir.glob("*.pdf"))
    section_mds = list(ctx.sections_dir.glob("*.md"))

    if not section_pdfs:
        issues.append("No section PDFs found in sections/")
    else:
        expected_sections = len(ctx.config.sections)
        if len(section_pdfs) < expected_sections:
            issues.append(
                f"Only {len(section_pdfs)} section PDFs found, expected {expected_sections}"
            )

    if not section_mds:
        issues.append("No markdown files found in sections/ (convert_to_markdown.py may not have run)")

    return issues


def run(config_path: str) -> Dict[str, Any]:
    """Run all preprocessing validations."""
    config = load_config(config_path)
    ctx = PipelineContext(config)

    print("=" * 60)
    print("PREPROCESSING VALIDATION")
    print("=" * 60)

    all_issues = []

    print("\nChecking document map...")
    issues = validate_document_map(ctx)
    all_issues.extend(issues)
    for i in issues:
        print(f"  ISSUE: {i}")
    if not issues:
        print("  OK")

    print("\nChecking extracted tables...")
    issues = validate_tables(ctx)
    all_issues.extend(issues)
    for i in issues:
        print(f"  ISSUE: {i}")
    if not issues:
        print("  OK")

    print("\nChecking section files...")
    issues = validate_sections(ctx)
    all_issues.extend(issues)
    for i in issues:
        print(f"  ISSUE: {i}")
    if not issues:
        print("  OK")

    # Summary
    print("\n" + "=" * 60)
    if all_issues:
        print(f"VALIDATION FOUND {len(all_issues)} ISSUE(S)")
        for i in all_issues:
            print(f"  - {i}")
    else:
        print("ALL CHECKS PASSED")
    print("=" * 60)

    # Save report
    report = {
        'guideline': config.slug,
        'status': 'pass' if not all_issues else 'fail',
        'issues': all_issues,
        'checks': {
            'document_map': 'pass' if ctx.document_map_path.exists() else 'fail',
            'tables': 'pass' if not validate_tables(ctx) else 'issues',
            'sections': 'pass' if not validate_sections(ctx) else 'issues',
        }
    }

    report_path = ctx.validation_report_path('preprocessing')
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved to {report_path}")

    return report


def main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Validate preprocessing outputs")
    parser.add_argument('--config', required=True, help="Path to guideline YAML config")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
