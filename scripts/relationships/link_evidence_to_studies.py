"""
Link Evidence Bodies to Studies

Creates INCLUDES relationships from EvidenceBodies to Studies using
reference number matching. Evidence bodies cite studies by reference
number (e.g., [45, 67, 89]).
"""

import json
import re
import sys
from pathlib import Path
from typing import List, Set

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.pipeline.config_loader import load_config
from scripts.pipeline.pipeline_context import PipelineContext


def extract_reference_numbers(text: str) -> Set[int]:
    """
    Extract reference numbers from text with bracket notation.

    Handles formats like [45], [45,67], [45-49], [45, 67, 89].
    """
    numbers = set()

    # Find bracketed references: [45], [45,67], [45-49]
    brackets = re.findall(r'\[([0-9,\s\-]+)\]', text)
    for bracket in brackets:
        parts = bracket.split(',')
        for part in parts:
            part = part.strip()
            if '-' in part:
                # Range: 45-49
                try:
                    start, end = part.split('-')
                    for n in range(int(start.strip()), int(end.strip()) + 1):
                        numbers.add(n)
                except (ValueError, TypeError):
                    pass
            else:
                try:
                    numbers.add(int(part))
                except ValueError:
                    pass

    return numbers


def link_evidence_to_studies(
    evidence_bodies: list,
    studies: list,
) -> List[dict]:
    """
    Create INCLUDES relationships (EvidenceBody -> Study).

    Uses reference numbers from evidence body text/metadata to link
    to studies by their ref_number.

    Args:
        evidence_bodies: List of evidence body dicts
        studies: List of study dicts

    Returns:
        List of relationship dicts
    """
    # Build study lookup by ref_number
    study_by_ref = {}
    for study in studies:
        ref_num = study.get('ref_number')
        if ref_num:
            study_by_ref[ref_num] = study

    relationships = []

    for eb in evidence_bodies:
        kq_num = eb.get('kq_number')

        # Get reference numbers from the evidence body
        ref_nums = set()

        # From explicit reference_numbers field
        if 'reference_numbers' in eb and isinstance(eb['reference_numbers'], list):
            ref_nums.update(eb['reference_numbers'])

        # From key_findings text
        if 'key_findings' in eb:
            ref_nums.update(extract_reference_numbers(str(eb['key_findings'])))

        # From confidence_level text
        if 'confidence_level' in eb:
            ref_nums.update(extract_reference_numbers(str(eb['confidence_level'])))

        for ref_num in sorted(ref_nums):
            if ref_num in study_by_ref:
                confidence = 0.9  # High confidence for explicit reference match
            else:
                confidence = 0.3  # Reference number not found in studies
                continue  # Skip unmatched references

            relationships.append({
                'type': 'INCLUDES',
                'from_type': 'EvidenceBody',
                'from_number': kq_num,
                'to_type': 'Study',
                'to_number': ref_num,
                'confidence': confidence,
            })

    return relationships


def run(config_path: str):
    """Run evidence-to-study linking."""
    config = load_config(config_path)
    ctx = PipelineContext(config)

    if not ctx.evidence_bodies_json.exists():
        print("ERROR: evidence_bodies.json not found")
        return None
    if not ctx.studies_json.exists():
        print("ERROR: studies.json not found")
        return None

    with open(ctx.evidence_bodies_json) as f:
        ebs = json.load(f)
    with open(ctx.studies_json) as f:
        studies = json.load(f)

    print("=" * 60)
    print("LINKING EVIDENCE BODIES TO STUDIES")
    print("=" * 60)
    print(f"Evidence Bodies: {len(ebs)}")
    print(f"Studies: {len(studies)}")

    rels = link_evidence_to_studies(ebs, studies)

    # Summary by EB
    by_eb = {}
    for r in rels:
        eb_num = r['from_number']
        by_eb[eb_num] = by_eb.get(eb_num, 0) + 1

    print(f"\nTotal INCLUDES relationships: {len(rels)}")
    for eb_num in sorted(by_eb.keys()):
        print(f"  EB (KQ {eb_num}): {by_eb[eb_num]} studies linked")

    return rels


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Link evidence bodies to studies")
    parser.add_argument('--config', required=True, help="Path to guideline YAML config")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
