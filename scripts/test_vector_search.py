"""Test vector search capability in Neo4j using GenAI plugin + OpenAI embeddings.

Creates sample Recommendation nodes, generates embeddings via ai.text.embed(),
stores them, runs similarity searches, and cleans up.

Requires:
    - Running Neo4j with GenAI plugin (docker-compose up -d)
    - Schema initialized (python scripts/init_schema.py)
    - OPENAI_API_KEY in .env

Usage:
    python scripts/test_vector_search.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Add project root to path for utils import
sys.path.insert(0, str(PROJECT_ROOT))
from utils.embeddings import embed_node_property, similarity_search, pairwise_cosine_similarity

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Test data: sample recommendations with varying semantic similarity
TEST_RECOMMENDATIONS = [
    {
        "rec_id": "TEST_REC_001",
        "rec_number": 901,
        "rec_text": "We recommend metformin as first-line pharmacotherapy for adults with newly diagnosed type 2 diabetes mellitus.",
        "strength": "Strong",
        "direction": "For",
        "category": "Not changed",
        "topic": "Pharmacotherapy",
        "module_id": "TEST_MOD",
        "guideline_id": "TEST_CPG",
        "version": "1.0",
        "version_date": "2023-05-01",
        "status": "Active",
    },
    {
        "rec_id": "TEST_REC_002",
        "rec_number": 902,
        "rec_text": "We suggest GLP-1 receptor agonists for patients with type 2 diabetes and established cardiovascular disease.",
        "strength": "Weak",
        "direction": "For",
        "category": "New-added",
        "topic": "Pharmacotherapy",
        "module_id": "TEST_MOD",
        "guideline_id": "TEST_CPG",
        "version": "1.0",
        "version_date": "2023-05-01",
        "status": "Active",
    },
    {
        "rec_id": "TEST_REC_003",
        "rec_number": 903,
        "rec_text": "We recommend diabetes self-management education and support programs for all patients with type 2 diabetes.",
        "strength": "Strong",
        "direction": "For",
        "category": "Not changed",
        "topic": "Self-Management",
        "module_id": "TEST_MOD",
        "guideline_id": "TEST_CPG",
        "version": "1.0",
        "version_date": "2023-05-01",
        "status": "Active",
    },
    {
        "rec_id": "TEST_REC_004",
        "rec_number": 904,
        "rec_text": "We recommend regular physical activity and dietary modifications as part of comprehensive lifestyle intervention.",
        "strength": "Strong",
        "direction": "For",
        "category": "Not changed",
        "topic": "Lifestyle",
        "module_id": "TEST_MOD",
        "guideline_id": "TEST_CPG",
        "version": "1.0",
        "version_date": "2023-05-01",
        "status": "Active",
    },
]


def create_test_nodes(driver):
    """Create test Recommendation nodes."""
    print("\n1. Creating test Recommendation nodes...")
    with driver.session() as session:
        for rec in TEST_RECOMMENDATIONS:
            session.run(
                """
                MERGE (r:Recommendation {rec_id: $rec_id})
                SET r += {
                    rec_number: $rec_number,
                    rec_text: $rec_text,
                    strength: $strength,
                    direction: $direction,
                    category: $category,
                    topic: $topic,
                    module_id: $module_id,
                    guideline_id: $guideline_id,
                    version: $version,
                    version_date: date($version_date),
                    status: $status
                }
                """,
                **rec,
            )
            print(f"   Created: {rec['rec_id']} - {rec['rec_text'][:60]}...")
    print(f"   Total: {len(TEST_RECOMMENDATIONS)} nodes")


def generate_embeddings(driver):
    """Generate embeddings for all test nodes using ai.text.embed()."""
    print("\n2. Generating embeddings via GenAI plugin (OpenAI)...")
    with driver.session() as session:
        for rec in TEST_RECOMMENDATIONS:
            result = embed_node_property(
                session,
                label="Recommendation",
                id_property="rec_id",
                id_value=rec["rec_id"],
                text_property="rec_text",
                api_key=OPENAI_API_KEY,
            )
            if result:
                print(f"   Embedded: {result['id']} ({result['dimensions']} dimensions)")
            else:
                print(f"   FAILED: {rec['rec_id']}")


def test_vector_index_search(driver):
    """Test approximate nearest neighbor search via vector index."""
    print("\n3. Testing vector index search (db.index.vector.queryNodes)...")
    query_text = "What medication should be used first for diabetes treatment?"
    print(f'   Query: "{query_text}"')

    with driver.session() as session:
        results = similarity_search(
            session,
            index_name="recommendation_embedding",
            query_text=query_text,
            top_k=4,
            api_key=OPENAI_API_KEY,
        )
        print(f"   Results ({len(results)} matches):")
        for node, score in results:
            print(f"     {score:.4f} - [{node['rec_id']}] {node['rec_text'][:70]}...")


def test_pairwise_similarity(driver):
    """Test exact pairwise cosine similarity via native Cypher function."""
    print("\n4. Testing pairwise cosine similarity (vector.similarity.cosine)...")
    pairs = [
        ("TEST_REC_001", "TEST_REC_002", "Both pharmacotherapy"),
        ("TEST_REC_001", "TEST_REC_003", "Pharma vs self-management"),
        ("TEST_REC_003", "TEST_REC_004", "Both lifestyle/education"),
        ("TEST_REC_001", "TEST_REC_004", "Pharma vs lifestyle"),
    ]
    with driver.session() as session:
        for id1, id2, desc in pairs:
            sim = pairwise_cosine_similarity(
                session,
                label="Recommendation",
                id1=id1,
                id2=id2,
                id_property="rec_id",
            )
            print(f"   {id1} vs {id2} ({desc}): {sim:.4f}")


def cleanup_test_data(driver):
    """Remove all test nodes."""
    print("\n5. Cleaning up test data...")
    with driver.session() as session:
        result = session.run(
            """
            MATCH (r:Recommendation)
            WHERE r.rec_id STARTS WITH 'TEST_'
            DETACH DELETE r
            RETURN count(*) AS deleted
            """
        )
        count = result.single()["deleted"]
        print(f"   Deleted {count} test nodes.")


def main():
    if not NEO4J_PASSWORD:
        print("Error: NEO4J_PASSWORD not set. Check your .env file.")
        sys.exit(1)
    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY not set. Check your .env file.")
        sys.exit(1)

    print(f"Connecting to Neo4j at {NEO4J_URI}...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        driver.verify_connectivity()
        print("Connected successfully.")
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

    try:
        create_test_nodes(driver)
        generate_embeddings(driver)
        test_vector_index_search(driver)
        test_pairwise_similarity(driver)
    finally:
        cleanup_test_data(driver)
        driver.close()

    print("\nAll vector search tests completed successfully.")


if __name__ == "__main__":
    main()
