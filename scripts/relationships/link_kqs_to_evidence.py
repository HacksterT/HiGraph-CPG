"""
Link Key Questions to Evidence Bodies

Creates ANSWERS relationships from EvidenceBodies to KeyQuestions.
This is a direct 1:1 mapping based on kq_number — each evidence body
explicitly addresses one key question.
"""

import json
import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.pipeline.config_loader import load_config
from scripts.pipeline.pipeline_context import PipelineContext


def link_kqs_to_evidence(key_questions: list, evidence_bodies: list) -> List[dict]:
    """
    Create ANSWERS relationships (EvidenceBody -> KeyQuestion).

    Each evidence body has a kq_number field indicating which KQ it addresses.
    This is a 1:1 structural relationship from the document.

    Args:
        key_questions: List of KQ dicts
        evidence_bodies: List of evidence body dicts

    Returns:
        List of relationship dicts
    """
    relationships = []

    kq_numbers = {kq['kq_number'] for kq in key_questions if 'kq_number' in kq}

    for eb in evidence_bodies:
        kq_num = eb.get('kq_number')
        if kq_num is None:
            continue

        confidence = 1.0 if kq_num in kq_numbers else 0.3

        relationships.append({
            'type': 'ANSWERS',
            'from_type': 'EvidenceBody',
            'from_number': kq_num,  # EB numbered by KQ
            'to_type': 'KeyQuestion',
            'to_number': kq_num,
            'confidence': confidence,
        })

    return relationships


def run(config_path: str):
    """Run KQ-to-evidence linking."""
    config = load_config(config_path)
    ctx = PipelineContext(config)

    if not ctx.key_questions_json.exists():
        print("ERROR: key_questions.json not found")
        return None
    if not ctx.evidence_bodies_json.exists():
        print("ERROR: evidence_bodies.json not found")
        return None

    with open(ctx.key_questions_json) as f:
        kqs = json.load(f)
    with open(ctx.evidence_bodies_json) as f:
        ebs = json.load(f)

    print("=" * 60)
    print("LINKING KEY QUESTIONS TO EVIDENCE BODIES")
    print("=" * 60)

    rels = link_kqs_to_evidence(kqs, ebs)
    print(f"Created {len(rels)} ANSWERS relationships (1:1 KQ-to-EB mapping)")

    return rels


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Link KQs to evidence bodies")
    parser.add_argument('--config', required=True, help="Path to guideline YAML config")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
