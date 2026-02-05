"""
Populate Study Nodes

Creates Study nodes from extracted citation data (with PubMed enrichment).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.pipeline.config_loader import load_config
from scripts.pipeline.pipeline_context import PipelineContext
from scripts.graph_population.neo4j_client import get_driver, merge_node


def run(config_path: str):
    """Populate Study nodes in Neo4j."""
    config = load_config(config_path)
    ctx = PipelineContext(config)

    if not ctx.studies_json.exists():
        print("ERROR: studies.json not found. Run extract_studies.py first.")
        return

    with open(ctx.studies_json) as f:
        studies = json.load(f)

    print(f"Populating {len(studies)} Study nodes...")
    driver = get_driver()

    # Process in batches to avoid transaction size issues
    batch_size = 50
    with driver.session() as session:
        for i in range(0, len(studies), batch_size):
            batch = studies[i:i + batch_size]
            with session.begin_transaction() as tx:
                for study in batch:
                    ref_num = study.get('ref_number', 0)
                    study_id = ctx.entity_id('STUDY', ref_num)

                    # Map study_type to schema enum
                    study_type = study.get('study_type')
                    valid_types = ['RCT', 'Systematic Review', 'Cohort', 'Cross-sectional']
                    if study_type == 'Meta-analysis':
                        study_type = 'Systematic Review'  # Closest match
                    elif study_type == 'Case-control':
                        study_type = 'Cohort'  # Closest match
                    elif study_type not in valid_types:
                        study_type = None

                    props = {
                        'study_id': study_id,
                        'title': study.get('title', ''),
                        'authors': study.get('authors', ''),
                        'journal': study.get('journal', ''),
                        'year': study.get('year', 0),
                        'pmid': study.get('pmid'),
                        'doi': study.get('doi'),
                    }

                    if study_type:
                        props['study_type'] = study_type
                    if study.get('abstract'):
                        props['abstract'] = study['abstract']

                    merge_node(tx, 'Study', 'study_id', study_id, props)

                tx.commit()
            print(f"  Batch {i//batch_size + 1}: {len(batch)} studies")

    print(f"  Created {len(studies)} Study nodes")
    driver.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Populate Study nodes")
    parser.add_argument('--config', required=True, help="Path to guideline YAML config")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
