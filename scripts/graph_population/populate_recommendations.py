"""
Populate Recommendation Nodes

Creates Recommendation nodes from extracted data. Uses MERGE for idempotency.
Entity IDs follow the pattern: {GUIDELINE_ID}_REC_{NUMBER}
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.pipeline.config_loader import load_config
from scripts.pipeline.pipeline_context import PipelineContext
from scripts.graph_population.neo4j_client import get_driver, merge_node


def run(config_path: str):
    """Populate Recommendation nodes in Neo4j."""
    config = load_config(config_path)
    ctx = PipelineContext(config)

    if not ctx.recommendations_json.exists():
        print("ERROR: recommendations.json not found. Run extract_recommendations.py first.")
        return

    with open(ctx.recommendations_json) as f:
        recs = json.load(f)

    print(f"Populating {len(recs)} Recommendation nodes...")
    driver = get_driver()

    with driver.session() as session:
        with session.begin_transaction() as tx:
            for rec in recs:
                rec_num = rec.get('rec_number', 0)
                rec_id = ctx.entity_id('REC', rec_num)

                props = {
                    'rec_id': rec_id,
                    'rec_number': rec_num,
                    'rec_text': rec.get('rec_text', ''),
                    'strength': rec.get('strength', ''),
                    'direction': rec.get('direction', ''),
                    'topic': rec.get('topic', ''),
                    'subtopic': rec.get('subtopic'),
                    'category': rec.get('category', ''),
                    'guideline_id': config.id,
                    'version': config.version,
                    'version_date': config.publication_date,
                    'status': 'Active',
                }

                merge_node(tx, 'Recommendation', 'rec_id', rec_id, props)

            tx.commit()

    print(f"  Created {len(recs)} Recommendation nodes")
    driver.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Populate Recommendation nodes")
    parser.add_argument('--config', required=True, help="Path to guideline YAML config")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
