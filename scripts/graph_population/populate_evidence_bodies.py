"""
Populate Evidence Body Nodes

Creates EvidenceBody nodes from extracted evidence synthesis data.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.pipeline.config_loader import load_config
from scripts.pipeline.pipeline_context import PipelineContext
from scripts.graph_population.neo4j_client import get_driver, merge_node


def run(config_path: str):
    """Populate EvidenceBody nodes in Neo4j."""
    config = load_config(config_path)
    ctx = PipelineContext(config)

    if not ctx.evidence_bodies_json.exists():
        print("ERROR: evidence_bodies.json not found. Run extract_evidence_bodies.py first.")
        return

    with open(ctx.evidence_bodies_json) as f:
        ebs = json.load(f)

    print(f"Populating {len(ebs)} EvidenceBody nodes...")
    driver = get_driver()

    with driver.session() as session:
        with session.begin_transaction() as tx:
            for eb in ebs:
                kq_num = eb.get('kq_number', 0)
                evidence_id = ctx.entity_id('EVB', kq_num)

                # Convert list fields to strings
                study_types = eb.get('study_types', [])
                if isinstance(study_types, list):
                    study_types = ', '.join(study_types)

                props = {
                    'evidence_id': evidence_id,
                    'topic': eb.get('topic', ''),
                    'quality_rating': eb.get('quality_rating', ''),
                    'confidence_level': eb.get('confidence_level', ''),
                    'num_studies': eb.get('num_studies', 0),
                    'study_types': study_types,
                    'population_description': eb.get('population_description', ''),
                    'key_findings': eb.get('key_findings', ''),
                    'guideline_id': config.id,
                    'kq_id': ctx.entity_id('KQ', kq_num),
                    'version': config.version,
                    'date_synthesized': config.publication_date,
                }

                merge_node(tx, 'EvidenceBody', 'evidence_id', evidence_id, props)

            tx.commit()

    print(f"  Created {len(ebs)} EvidenceBody nodes")
    driver.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Populate EvidenceBody nodes")
    parser.add_argument('--config', required=True, help="Path to guideline YAML config")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
