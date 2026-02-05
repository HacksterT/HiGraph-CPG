"""
Populate Intervention Nodes (V2 Schema)

Creates Intervention nodes from interventions.json.
Interventions represent treatments, medications, lifestyle changes, devices, and procedures.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.pipeline.config_loader import load_config
from scripts.pipeline.pipeline_context import PipelineContext
from scripts.graph_population.neo4j_client import get_driver, merge_node


def run(config_path: str):
    """Populate Intervention nodes in Neo4j."""
    config = load_config(config_path)
    ctx = PipelineContext(config)

    # V2 data file
    interventions_file = ctx.extracted_dir / "interventions.json"
    if not interventions_file.exists():
        print(f"ERROR: interventions.json not found at {interventions_file}")
        return

    with open(interventions_file) as f:
        interventions = json.load(f)

    print(f"Populating {len(interventions)} Intervention nodes...")
    driver = get_driver()

    with driver.session() as session:
        with session.begin_transaction() as tx:
            for intv in interventions:
                props = {
                    "intervention_id": intv["intervention_id"],
                    "name": intv["name"],
                    "type": intv["type"],
                    "description": intv.get("description"),
                    "mechanism": intv.get("mechanism"),
                    "drug_class": intv.get("drug_class"),  # Only for type=drug
                }
                merge_node(tx, "Intervention", "intervention_id", intv["intervention_id"], props)

            tx.commit()

    print(f"  Created {len(interventions)} Intervention nodes")
    driver.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Populate Intervention nodes (V2)")
    parser.add_argument("--config", required=True, help="Path to guideline YAML config")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
