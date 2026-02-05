"""
Populate Relationships

Creates all relationships from relationships.json in Neo4j.
Uses MERGE for idempotency. Filters by confidence threshold.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.pipeline.config_loader import load_config
from scripts.pipeline.pipeline_context import PipelineContext
from scripts.graph_population.neo4j_client import get_driver, merge_relationship


# Map entity type + number to label + id property + id generation
ENTITY_TYPE_MAP = {
    'Guideline': ('Guideline', 'guideline_id'),
    'ClinicalModule': ('ClinicalModule', 'module_id'),
    'KeyQuestion': ('KeyQuestion', 'kq_id'),
    'EvidenceBody': ('EvidenceBody', 'evidence_id'),
    'Study': ('Study', 'study_id'),
    'Recommendation': ('Recommendation', 'rec_id'),
}

# Map entity type to ID prefix
ID_PREFIX_MAP = {
    'KeyQuestion': 'KQ',
    'EvidenceBody': 'EVB',
    'Study': 'STUDY',
    'Recommendation': 'REC',
}


def _resolve_entity_id(ctx, rel, direction: str) -> tuple:
    """
    Resolve the entity label, id property, and id value from a relationship dict.

    Args:
        ctx: PipelineContext
        rel: Relationship dict
        direction: 'from' or 'to'

    Returns:
        (label, id_property, id_value)
    """
    entity_type = rel.get(f'{direction}_type')
    label, id_prop = ENTITY_TYPE_MAP.get(entity_type, (entity_type, 'id'))

    # Try direct ID first (for structural relationships)
    direct_id = rel.get(f'{direction}_id')
    if direct_id:
        return label, id_prop, direct_id

    # Generate from number
    number = rel.get(f'{direction}_number')
    prefix = ID_PREFIX_MAP.get(entity_type)
    if prefix and number is not None:
        return label, id_prop, ctx.entity_id(prefix, number)

    return label, id_prop, None


def run(config_path: str):
    """Populate relationships in Neo4j."""
    config = load_config(config_path)
    ctx = PipelineContext(config)

    if not ctx.relationships_json.exists():
        print("ERROR: relationships.json not found. Run build_all_relationships.py first.")
        return

    with open(ctx.relationships_json) as f:
        rels = json.load(f)

    # Filter by confidence
    threshold = config.confidence_thresholds.flag_for_review
    eligible = [r for r in rels if r.get('confidence', 0) >= threshold]
    skipped = len(rels) - len(eligible)

    print(f"Populating {len(eligible)} relationships (skipped {skipped} low-confidence)...")
    driver = get_driver()

    created = 0
    errors = 0

    with driver.session() as session:
        with session.begin_transaction() as tx:
            for rel in eligible:
                from_label, from_id_prop, from_id = _resolve_entity_id(ctx, rel, 'from')
                to_label, to_id_prop, to_id = _resolve_entity_id(ctx, rel, 'to')

                if not from_id or not to_id:
                    errors += 1
                    continue

                rel_props = {}
                if 'confidence' in rel:
                    rel_props['confidence'] = rel['confidence']

                try:
                    merge_relationship(
                        tx,
                        from_label, from_id_prop, from_id,
                        to_label, to_id_prop, to_id,
                        rel['type'],
                        rel_props if rel_props else None,
                    )
                    created += 1
                except Exception as e:
                    errors += 1
                    print(f"  ERROR: {rel['type']} ({from_id} -> {to_id}): {e}")

            tx.commit()

    print(f"  Created: {created}")
    if errors:
        print(f"  Errors: {errors}")

    # Print summary by type
    by_type = {}
    for r in eligible:
        t = r['type']
        by_type[t] = by_type.get(t, 0) + 1
    print("\n  By type:")
    for t, count in sorted(by_type.items()):
        print(f"    {t}: {count}")

    driver.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Populate relationships in Neo4j")
    parser.add_argument('--config', required=True, help="Path to guideline YAML config")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
