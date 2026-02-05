"""
Populate Clinical Module Nodes

Creates ClinicalModule nodes from extracted metadata.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.pipeline.config_loader import load_config
from scripts.pipeline.pipeline_context import PipelineContext
from scripts.graph_population.neo4j_client import get_driver, merge_node


def run(config_path: str):
    """Populate ClinicalModule nodes in Neo4j."""
    config = load_config(config_path)
    ctx = PipelineContext(config)

    if not ctx.clinical_modules_json.exists():
        print("ERROR: clinical_modules.json not found. Run extract_guideline_metadata.py first.")
        return

    with open(ctx.clinical_modules_json) as f:
        modules = json.load(f)

    print(f"Populating {len(modules)} ClinicalModule nodes...")
    driver = get_driver()

    with driver.session() as session:
        with session.begin_transaction() as tx:
            for mod in modules:
                # Convert topics list to string for Neo4j (no list properties in Community)
                props = dict(mod)
                if 'topics' in props and isinstance(props['topics'], list):
                    props['topics'] = ', '.join(props['topics'])
                merge_node(tx, 'ClinicalModule', 'module_id', mod['module_id'], props)
            tx.commit()

    for mod in modules:
        print(f"  Created: {mod['module_id']} ({mod['module_name']})")

    driver.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Populate ClinicalModule nodes")
    parser.add_argument('--config', required=True, help="Path to guideline YAML config")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
