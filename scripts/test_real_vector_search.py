"""Test vector search on real populated data."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def test_recommendation_search(driver):
    """Test vector search on recommendations."""
    query_text = "medications for diabetic patients with kidney disease"
    config = {'token': OPENAI_API_KEY, 'model': 'text-embedding-3-small'}

    print(f'\nQuery: "{query_text}"')
    print('-' * 70)

    cypher = """
    CALL genai.vector.encodeBatch($texts, 'OpenAI', $config) YIELD vector AS queryEmbedding
    CALL db.index.vector.queryNodes('recommendation_embedding', 5, queryEmbedding)
    YIELD node, score
    RETURN node.rec_id as rec_id, node.topic as topic, node.strength as strength,
           score, left(node.rec_text, 80) as rec_text
    ORDER BY score DESC
    """

    with driver.session() as session:
        result = session.run(cypher, texts=[query_text], config=config)
        print("Top 5 Recommendations:")
        for record in result:
            print(f"  {record['score']:.4f} | {record['rec_id']} | {record['strength']} | {record['topic']}")
            print(f"         {record['rec_text']}...")


def test_study_search(driver):
    """Test vector search on studies."""
    query_text = "SGLT2 inhibitors cardiovascular outcomes"
    config = {'token': OPENAI_API_KEY, 'model': 'text-embedding-3-small'}

    print(f'\nQuery: "{query_text}"')
    print('-' * 70)

    cypher = """
    CALL genai.vector.encodeBatch($texts, 'OpenAI', $config) YIELD vector AS queryEmbedding
    CALL db.index.vector.queryNodes('study_embedding', 5, queryEmbedding)
    YIELD node, score
    RETURN node.study_id as study_id, node.title as title, node.year as year,
           node.journal as journal, score
    ORDER BY score DESC
    """

    with driver.session() as session:
        result = session.run(cypher, texts=[query_text], config=config)
        print("Top 5 Studies:")
        for record in result:
            title = record['title'][:70] if record['title'] else 'N/A'
            print(f"  {record['score']:.4f} | {record['year']} | {record['journal']}")
            print(f"         {title}...")


def main():
    if not NEO4J_PASSWORD or not OPENAI_API_KEY:
        print("Error: NEO4J_PASSWORD or OPENAI_API_KEY not set.")
        sys.exit(1)

    print(f"Connecting to Neo4j at {NEO4J_URI}...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        driver.verify_connectivity()
        print("Connected successfully.")

        print("\n" + "=" * 70)
        print("RECOMMENDATION VECTOR SEARCH")
        print("=" * 70)
        test_recommendation_search(driver)

        print("\n" + "=" * 70)
        print("STUDY VECTOR SEARCH")
        print("=" * 70)
        test_study_search(driver)

    finally:
        driver.close()

    print("\n\nVector search tests completed.")


if __name__ == "__main__":
    main()
