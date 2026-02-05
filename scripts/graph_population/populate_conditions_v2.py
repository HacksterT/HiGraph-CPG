"""
Populate Condition Nodes (V2 Schema)

Creates Condition nodes from conditions.json.
Conditions represent diseases/diagnoses with ICD-10 and SNOMED codes.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.pipeline.config_loader import load_config
from scripts.pipeline.pipeline_context import PipelineContext
from scripts.graph_population.neo4j_client import get_driver, merge_node


def run(config_path: str):
    """Populate Condition nodes in Neo4j."""
    config = load_config(config_path)
    ctx = PipelineContext(config)

    # V2 data file
    conditions_file = ctx.extracted_dir / "conditions.json"
    if not conditions_file.exists():
        print(f"ERROR: conditions.json not found at {conditions_file}")
        return

    with open(conditions_file) as f:
        conditions = json.load(f)

    print(f"Populating {len(conditions)} Condition nodes...")
    driver = get_driver()

    with driver.session() as session:
        with session.begin_transaction() as tx:
            for cond in conditions:
                props = {
                    "condition_id": cond["condition_id"],
                    "name": cond["name"],
                    "icd10_codes": cond.get("icd10_codes", []),
                    "snomed_ct": cond.get("snomed_ct"),
                    "definition": cond.get("definition"),
                    "diagnostic_criteria": cond.get("diagnostic_criteria"),
                }
                merge_node(tx, "Condition", "condition_id", cond["condition_id"], props)

            tx.commit()

    print(f"  Created {len(conditions)} Condition nodes")
    driver.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Populate Condition nodes (V2)")
    parser.add_argument("--config", required=True, help="Path to guideline YAML config")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
