"""
Populate Key Question Nodes

Creates KeyQuestion nodes from extracted data with PICOTS elements.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.pipeline.config_loader import load_config
from scripts.pipeline.pipeline_context import PipelineContext
from scripts.graph_population.neo4j_client import get_driver, merge_node


def run(config_path: str):
    """Populate KeyQuestion nodes in Neo4j."""
    config = load_config(config_path)
    ctx = PipelineContext(config)

    if not ctx.key_questions_json.exists():
        print("ERROR: key_questions.json not found. Run extract_key_questions.py first.")
        return

    with open(ctx.key_questions_json) as f:
        kqs = json.load(f)

    print(f"Populating {len(kqs)} KeyQuestion nodes...")
    driver = get_driver()

    with driver.session() as session:
        with session.begin_transaction() as tx:
            for kq in kqs:
                kq_num = kq.get('kq_number', 0)
                kq_id = ctx.entity_id('KQ', kq_num)

                # Convert list fields to strings for Neo4j Community Edition
                outcomes_critical = kq.get('outcomes_critical', [])
                outcomes_important = kq.get('outcomes_important', [])
                if isinstance(outcomes_critical, list):
                    outcomes_critical = '; '.join(outcomes_critical)
                if isinstance(outcomes_important, list):
                    outcomes_important = '; '.join(outcomes_important)

                props = {
                    'kq_id': kq_id,
                    'kq_number': kq_num,
                    'question_text': kq.get('question_text', ''),
                    'population': kq.get('population', ''),
                    'intervention': kq.get('intervention', ''),
                    'comparator': kq.get('comparator'),
                    'outcomes_critical': outcomes_critical,
                    'outcomes_important': outcomes_important,
                    'timing': kq.get('timing'),
                    'setting': kq.get('setting'),
                    'guideline_id': config.id,
                }

                # Find matching module
                kq_topic = (kq.get('topic') or '').lower()
                for mod in config.modules:
                    for topic in mod.topics:
                        if topic.lower() in kq_topic or kq_topic in topic.lower():
                            props['module_id'] = ctx.module_id(mod.id_suffix)
                            break

                merge_node(tx, 'KeyQuestion', 'kq_id', kq_id, props)

            tx.commit()

    print(f"  Created {len(kqs)} KeyQuestion nodes")
    driver.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Populate KeyQuestion nodes")
    parser.add_argument('--config', required=True, help="Path to guideline YAML config")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
