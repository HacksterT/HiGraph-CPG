"""
Build All Relationships

Aggregates all relationship inference scripts and also generates
structural relationships (PART_OF, CONTAINS) from config. Outputs
a single relationships.json with all links.
"""

import json
import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.pipeline.config_loader import load_config
from scripts.pipeline.pipeline_context import PipelineContext
from scripts.relationships.link_recommendations_to_kqs import link_recommendations_to_kqs
from scripts.relationships.link_kqs_to_evidence import link_kqs_to_evidence
from scripts.relationships.link_evidence_to_studies import link_evidence_to_studies


def build_structural_relationships(config, ctx: PipelineContext) -> List[dict]:
    """
    Build PART_OF and CONTAINS relationships from config structure.

    - ClinicalModule -[PART_OF]-> Guideline
    - ClinicalModule -[CONTAINS]-> KeyQuestion (via topic matching)
    """
    relationships = []

    # PART_OF: each module is part of the guideline
    for mod in config.modules:
        relationships.append({
            'type': 'PART_OF',
            'from_type': 'ClinicalModule',
            'from_id': ctx.module_id(mod.id_suffix),
            'to_type': 'Guideline',
            'to_id': config.id,
            'confidence': 1.0,
        })

    # CONTAINS: match KQs to modules via topic
    if ctx.key_questions_json.exists():
        with open(ctx.key_questions_json) as f:
            kqs = json.load(f)

        for kq in kqs:
            kq_topic = (kq.get('topic') or '').lower()
            best_module = None
            best_score = 0.0

            for mod in config.modules:
                for topic in mod.topics:
                    if topic.lower() in kq_topic or kq_topic in topic.lower():
                        score = 1.0
                    else:
                        # Partial word overlap
                        mod_words = set(topic.lower().split())
                        kq_words = set(kq_topic.split())
                        overlap = mod_words & kq_words
                        score = len(overlap) / max(len(mod_words), 1)

                    if score > best_score:
                        best_score = score
                        best_module = mod

            if best_module and best_score > 0.3:
                relationships.append({
                    'type': 'CONTAINS',
                    'from_type': 'ClinicalModule',
                    'from_id': ctx.module_id(best_module.id_suffix),
                    'to_type': 'KeyQuestion',
                    'to_number': kq.get('kq_number'),
                    'confidence': round(best_score, 3),
                })

    return relationships


def build_based_on_relationships(
    recommendations: list,
    leads_to_rels: list,
) -> List[dict]:
    """
    Build BASED_ON relationships (Recommendation -> EvidenceBody).

    Derived from LEADS_TO: if KQ N leads to Rec M, then Rec M is BASED_ON EB N
    (since EB and KQ have 1:1 mapping).
    """
    relationships = []

    for rel in leads_to_rels:
        if rel['type'] == 'LEADS_TO':
            relationships.append({
                'type': 'BASED_ON',
                'from_type': 'Recommendation',
                'from_number': rel['to_number'],
                'to_type': 'EvidenceBody',
                'to_number': rel['from_number'],  # EB number == KQ number
                'confidence': rel['confidence'],
            })

    return relationships


def run(config_path: str):
    """Build all relationships and save to relationships.json."""
    config = load_config(config_path)
    ctx = PipelineContext(config)
    ctx.ensure_directories()

    print("=" * 60)
    print("BUILDING ALL RELATIONSHIPS")
    print("=" * 60)

    all_relationships = []

    # Load entities
    recs = []
    kqs = []
    ebs = []
    studies = []

    if ctx.recommendations_json.exists():
        with open(ctx.recommendations_json) as f:
            recs = json.load(f)
    if ctx.key_questions_json.exists():
        with open(ctx.key_questions_json) as f:
            kqs = json.load(f)
    if ctx.evidence_bodies_json.exists():
        with open(ctx.evidence_bodies_json) as f:
            ebs = json.load(f)
    if ctx.studies_json.exists():
        with open(ctx.studies_json) as f:
            studies = json.load(f)

    # 1. Structural relationships
    print("\n1. Building structural relationships (PART_OF, CONTAINS)...")
    structural = build_structural_relationships(config, ctx)
    all_relationships.extend(structural)
    print(f"   {len(structural)} structural relationships")

    # 2. Recommendation -> KQ
    if recs and kqs:
        print("\n2. Linking recommendations to key questions (LEADS_TO)...")
        leads_to = link_recommendations_to_kqs(recs, kqs, config)
        all_relationships.extend(leads_to)
        print(f"   {len(leads_to)} LEADS_TO relationships")

        # 3. BASED_ON (derived from LEADS_TO)
        print("\n3. Deriving BASED_ON relationships...")
        based_on = build_based_on_relationships(recs, leads_to)
        all_relationships.extend(based_on)
        print(f"   {len(based_on)} BASED_ON relationships")
    else:
        leads_to = []

    # 4. KQ -> Evidence Body
    if kqs and ebs:
        print("\n4. Linking key questions to evidence bodies (ANSWERS)...")
        answers = link_kqs_to_evidence(kqs, ebs)
        all_relationships.extend(answers)
        print(f"   {len(answers)} ANSWERS relationships")

    # 5. Evidence Body -> Studies
    if ebs and studies:
        print("\n5. Linking evidence bodies to studies (INCLUDES)...")
        includes = link_evidence_to_studies(ebs, studies)
        all_relationships.extend(includes)
        print(f"   {len(includes)} INCLUDES relationships")

    # Save
    with open(ctx.relationships_json, 'w') as f:
        json.dump(all_relationships, f, indent=2)

    # Summary
    print("\n" + "=" * 60)
    print("RELATIONSHIP SUMMARY")
    print("=" * 60)

    by_type = {}
    for r in all_relationships:
        t = r['type']
        by_type[t] = by_type.get(t, 0) + 1
    for t, count in sorted(by_type.items()):
        print(f"  {t}: {count}")
    print(f"  TOTAL: {len(all_relationships)}")

    # Flag low-confidence
    thresholds = config.confidence_thresholds
    flagged = [r for r in all_relationships
               if thresholds.flag_for_review <= r.get('confidence', 0) < thresholds.auto_accept]
    low = [r for r in all_relationships if r.get('confidence', 0) < thresholds.flag_for_review]

    if flagged:
        flagged_path = ctx.manual_review_dir / "low_confidence_links.json"
        with open(flagged_path, 'w') as f:
            json.dump(flagged, f, indent=2)
        print(f"\n{len(flagged)} flagged for review -> {flagged_path}")

    if low:
        print(f"{len(low)} low-confidence links excluded")

    print(f"\nRelationships saved to {ctx.relationships_json}")
    return all_relationships


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build all relationships")
    parser.add_argument('--config', required=True, help="Path to guideline YAML config")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
