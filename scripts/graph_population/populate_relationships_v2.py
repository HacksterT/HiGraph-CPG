"""
Populate Relationships (V2 Schema)

Creates all relationships from relationships_v2.json.
Includes new relationship types: PRIMARILY_ABOUT, REFERENCES, PRECURSOR_TO,
MAY_DEVELOP, ASSOCIATED_WITH, BELONGS_TO, RELEVANT_TO, APPLIES_TO, RECOMMENDS.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.pipeline.config_loader import load_config
from scripts.pipeline.pipeline_context import PipelineContext
from scripts.graph_population.neo4j_client import get_driver, merge_relationship

# Node type to ID property mapping
NODE_ID_PROPERTIES = {
    "Guideline": "guideline_id",
    "ClinicalModule": "module_id",
    "CarePhase": "phase_id",
    "Recommendation": "rec_id",
    "KeyQuestion": "kq_id",
    "EvidenceBody": "eb_id",
    "Study": "study_id",
    "Intervention": "intervention_id",
    "Condition": "condition_id",
}


def run(config_path: str):
    """Populate V2 relationships in Neo4j."""
    config = load_config(config_path)
    ctx = PipelineContext(config)

    # V2 relationships file
    relationships_file = ctx.extracted_dir / "relationships_v2.json"
    if not relationships_file.exists():
        print(f"ERROR: relationships_v2.json not found at {relationships_file}")
        return

    with open(relationships_file) as f:
        data = json.load(f)

    relationships = data.get("relationships", [])
    # Filter out comment entries
    relationships = [r for r in relationships if "_comment" not in r]

    print(f"Populating {len(relationships)} V2 relationships...")
    driver = get_driver()

    created = 0
    skipped = 0
    errors = []

    with driver.session() as session:
        with session.begin_transaction() as tx:
            for rel in relationships:
                from_type = rel["from_type"]
                from_id = rel["from_id"]
                to_type = rel["to_type"]
                to_id = rel["to_id"]
                rel_type = rel["type"]
                rel_props = rel.get("properties")

                from_id_prop = NODE_ID_PROPERTIES.get(from_type)
                to_id_prop = NODE_ID_PROPERTIES.get(to_type)

                if not from_id_prop:
                    errors.append(f"Unknown from_type: {from_type}")
                    skipped += 1
                    continue

                if not to_id_prop:
                    errors.append(f"Unknown to_type: {to_type}")
                    skipped += 1
                    continue

                try:
                    merge_relationship(
                        tx,
                        from_type, from_id_prop, from_id,
                        to_type, to_id_prop, to_id,
                        rel_type,
                        rel_props
                    )
                    created += 1
                except Exception as e:
                    errors.append(f"{from_type}({from_id})-[{rel_type}]->{to_type}({to_id}): {e}")
                    skipped += 1

            tx.commit()

    print(f"  Created: {created}")
    print(f"  Skipped: {skipped}")
    if errors[:5]:  # Show first 5 errors
        print("  Sample errors:")
        for err in errors[:5]:
            print(f"    - {err}")

    driver.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Populate V2 relationships")
    parser.add_argument("--config", required=True, help="Path to guideline YAML config")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
