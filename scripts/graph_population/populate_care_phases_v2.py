"""
Populate CarePhase Nodes (V2 Schema)

Creates CarePhase nodes from care_phases.json.
CarePhases represent the clinical workflow stages for managing a condition.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.pipeline.config_loader import load_config
from scripts.pipeline.pipeline_context import PipelineContext
from scripts.graph_population.neo4j_client import get_driver, merge_node


def run(config_path: str):
    """Populate CarePhase nodes in Neo4j."""
    config = load_config(config_path)
    ctx = PipelineContext(config)

    # V2 data file
    care_phases_file = ctx.extracted_dir / "care_phases.json"
    if not care_phases_file.exists():
        print(f"ERROR: care_phases.json not found at {care_phases_file}")
        return

    with open(care_phases_file) as f:
        phases = json.load(f)

    print(f"Populating {len(phases)} CarePhase nodes...")
    driver = get_driver()

    with driver.session() as session:
        with session.begin_transaction() as tx:
            for phase in phases:
                props = {
                    "phase_id": phase["phase_id"],
                    "guideline_id": phase["guideline_id"],
                    "name": phase["name"],
                    "description": phase["description"],
                    "sequence_order": phase["sequence_order"],
                }
                merge_node(tx, "CarePhase", "phase_id", phase["phase_id"], props)

            tx.commit()

    print(f"  Created {len(phases)} CarePhase nodes")
    driver.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Populate CarePhase nodes (V2)")
    parser.add_argument("--config", required=True, help="Path to guideline YAML config")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
