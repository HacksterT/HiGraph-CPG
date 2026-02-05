"""
Generate Embeddings for Graph Nodes

Runs as a separate stage after graph population. Calls the Neo4j GenAI
plugin to generate embeddings via OpenAI's text-embedding-3-small model
and stores them on nodes via db.create.setNodeVectorProperty().
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

load_dotenv()

from scripts.pipeline.config_loader import load_config
from scripts.pipeline.pipeline_context import PipelineContext
from scripts.graph_population.neo4j_client import get_driver
from utils.embeddings import batch_embed_nodes


# Node types and their text properties to embed
EMBEDDING_TARGETS = [
    {
        'label': 'Recommendation',
        'text_property': 'rec_text',
        'embedding_property': 'embedding',
    },
    {
        'label': 'KeyQuestion',
        'text_property': 'question_text',
        'embedding_property': 'embedding',
    },
    {
        'label': 'EvidenceBody',
        'text_property': 'key_findings',
        'embedding_property': 'embedding',
    },
]


def run(config_path: str):
    """Generate embeddings for all target node types."""
    config = load_config(config_path)
    ctx = PipelineContext(config)

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set. Required for embedding generation.")
        return

    print("=" * 60)
    print("GENERATING EMBEDDINGS")
    print("=" * 60)

    driver = get_driver()

    for target in EMBEDDING_TARGETS:
        label = target['label']
        text_prop = target['text_property']
        emb_prop = target['embedding_property']

        print(f"\nEmbedding {label} nodes (property: {text_prop})...")

        try:
            with driver.session() as session:
                result = session.execute_write(
                    batch_embed_nodes,
                    label=label,
                    text_property=text_prop,
                    embedding_property=emb_prop,
                    api_key=api_key,
                )
                if result:
                    count = result.get('embedded_count', 0)
                    print(f"  Embedded {count} {label} nodes")
                else:
                    print(f"  No {label} nodes needed embedding")
        except Exception as e:
            print(f"  ERROR embedding {label}: {e}")
            print("  (This may be expected if Neo4j GenAI plugin is not installed)")

    driver.close()
    print("\nEmbedding generation complete")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate embeddings for graph nodes")
    parser.add_argument('--config', required=True, help="Path to guideline YAML config")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
