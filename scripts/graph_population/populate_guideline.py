"""
Populate Guideline Node

Creates the top-level Guideline node from extracted metadata.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.pipeline.config_loader import load_config
from scripts.pipeline.pipeline_context import PipelineContext
from scripts.graph_population.neo4j_client import get_driver, merge_node


def run(config_path: str):
    """Populate Guideline node in Neo4j."""
    config = load_config(config_path)
    ctx = PipelineContext(config)

    if not ctx.guideline_json.exists():
        print("ERROR: guideline.json not found. Run extract_guideline_metadata.py first.")
        return

    with open(ctx.guideline_json) as f:
        guideline = json.load(f)

    print("Populating Guideline node...")
    driver = get_driver()

    with driver.session() as session:
        with session.begin_transaction() as tx:
            merge_node(tx, 'Guideline', 'guideline_id', guideline['guideline_id'], guideline)
            tx.commit()

    print(f"  Created Guideline: {guideline['guideline_id']}")
    driver.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Populate Guideline node")
    parser.add_argument('--config', required=True, help="Path to guideline YAML config")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
