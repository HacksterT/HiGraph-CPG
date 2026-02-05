"""
Initialize Neo4j Schema V2 for HiGraph-CPG

This script creates all constraints, indexes, full-text indexes, and vector indexes
for the V2 schema. It's idempotent - safe to run multiple times.

Usage:
    .venv/Scripts/python.exe scripts/init_schema_v2.py
"""

import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()


def get_driver():
    """Get Neo4j driver from environment variables."""
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")

    if not password:
        raise ValueError("NEO4J_PASSWORD environment variable is required")

    return GraphDatabase.driver(uri, auth=(user, password))


# =============================================================================
# SCHEMA DEFINITIONS
# =============================================================================

CONSTRAINTS = [
    # Node type unique constraints
    ("guideline_id_unique", "CREATE CONSTRAINT guideline_id_unique IF NOT EXISTS FOR (g:Guideline) REQUIRE g.guideline_id IS UNIQUE"),
    ("carephase_id_unique", "CREATE CONSTRAINT carephase_id_unique IF NOT EXISTS FOR (cp:CarePhase) REQUIRE cp.phase_id IS UNIQUE"),
    ("recommendation_id_unique", "CREATE CONSTRAINT recommendation_id_unique IF NOT EXISTS FOR (r:Recommendation) REQUIRE r.rec_id IS UNIQUE"),
    ("keyquestion_id_unique", "CREATE CONSTRAINT keyquestion_id_unique IF NOT EXISTS FOR (kq:KeyQuestion) REQUIRE kq.kq_id IS UNIQUE"),
    ("evidencebody_id_unique", "CREATE CONSTRAINT evidencebody_id_unique IF NOT EXISTS FOR (eb:EvidenceBody) REQUIRE eb.eb_id IS UNIQUE"),
    ("study_id_unique", "CREATE CONSTRAINT study_id_unique IF NOT EXISTS FOR (s:Study) REQUIRE s.study_id IS UNIQUE"),
    ("intervention_id_unique", "CREATE CONSTRAINT intervention_id_unique IF NOT EXISTS FOR (i:Intervention) REQUIRE i.intervention_id IS UNIQUE"),
    ("condition_id_unique", "CREATE CONSTRAINT condition_id_unique IF NOT EXISTS FOR (c:Condition) REQUIRE c.condition_id IS UNIQUE"),
]

PROPERTY_INDEXES = [
    # Study indexes
    ("study_pmid", "CREATE INDEX study_pmid IF NOT EXISTS FOR (s:Study) ON (s.pmid)"),
    ("study_year", "CREATE INDEX study_year IF NOT EXISTS FOR (s:Study) ON (s.year)"),
    ("study_type", "CREATE INDEX study_type IF NOT EXISTS FOR (s:Study) ON (s.study_type)"),
    # Recommendation indexes
    ("rec_strength_direction", "CREATE INDEX rec_strength_direction IF NOT EXISTS FOR (r:Recommendation) ON (r.strength_direction)"),
    ("rec_category", "CREATE INDEX rec_category IF NOT EXISTS FOR (r:Recommendation) ON (r.category)"),
    ("rec_topic", "CREATE INDEX rec_topic IF NOT EXISTS FOR (r:Recommendation) ON (r.topic)"),
    # EvidenceBody indexes
    ("eb_quality", "CREATE INDEX eb_quality IF NOT EXISTS FOR (eb:EvidenceBody) ON (eb.quality_rating)"),
    # Intervention indexes
    ("intervention_type", "CREATE INDEX intervention_type IF NOT EXISTS FOR (i:Intervention) ON (i.type)"),
    ("intervention_name", "CREATE INDEX intervention_name IF NOT EXISTS FOR (i:Intervention) ON (i.name)"),
    ("intervention_drug_class", "CREATE INDEX intervention_drug_class IF NOT EXISTS FOR (i:Intervention) ON (i.drug_class)"),
    # Condition indexes
    ("condition_name", "CREATE INDEX condition_name IF NOT EXISTS FOR (c:Condition) ON (c.name)"),
    ("condition_icd10", "CREATE INDEX condition_icd10 IF NOT EXISTS FOR (c:Condition) ON (c.icd10_codes)"),
    # CarePhase indexes
    ("carephase_sequence", "CREATE INDEX carephase_sequence IF NOT EXISTS FOR (cp:CarePhase) ON (cp.sequence_order)"),
]

FULLTEXT_INDEXES = [
    ("recommendation_fulltext", "CREATE FULLTEXT INDEX recommendation_fulltext IF NOT EXISTS FOR (r:Recommendation) ON EACH [r.rec_text]"),
    ("carephase_fulltext", "CREATE FULLTEXT INDEX carephase_fulltext IF NOT EXISTS FOR (cp:CarePhase) ON EACH [cp.name, cp.description]"),
    ("condition_fulltext", "CREATE FULLTEXT INDEX condition_fulltext IF NOT EXISTS FOR (c:Condition) ON EACH [c.name, c.definition, c.diagnostic_criteria]"),
    ("intervention_fulltext", "CREATE FULLTEXT INDEX intervention_fulltext IF NOT EXISTS FOR (i:Intervention) ON EACH [i.name, i.description, i.mechanism]"),
]

VECTOR_INDEXES = [
    ("recommendation_embedding", """
        CREATE VECTOR INDEX recommendation_embedding IF NOT EXISTS
        FOR (r:Recommendation) ON (r.embedding)
        OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}}
    """),
    ("study_embedding", """
        CREATE VECTOR INDEX study_embedding IF NOT EXISTS
        FOR (s:Study) ON (s.embedding)
        OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}}
    """),
    ("keyquestion_embedding", """
        CREATE VECTOR INDEX keyquestion_embedding IF NOT EXISTS
        FOR (kq:KeyQuestion) ON (kq.embedding)
        OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}}
    """),
    ("evidencebody_embedding", """
        CREATE VECTOR INDEX evidencebody_embedding IF NOT EXISTS
        FOR (eb:EvidenceBody) ON (eb.embedding)
        OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}}
    """),
]


def run_schema_commands(session, commands, command_type):
    """Execute a list of schema commands."""
    print(f"\nCreating {command_type}...")
    for name, cypher in commands:
        try:
            session.run(cypher)
            print(f"  ✓ {name}")
        except Exception as e:
            print(f"  ✗ {name}: {e}")


def wait_for_vector_indexes(session, timeout=120):
    """Wait for vector indexes to become ONLINE."""
    print("\nWaiting for vector indexes to become ONLINE...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        result = session.run("SHOW INDEXES")
        all_indexes = list(result)
        # Filter to vector indexes only
        indexes = [idx for idx in all_indexes if idx.get("type") == "VECTOR"]
        indexes = [{"name": idx["name"], "state": idx.get("state", "UNKNOWN")} for idx in indexes]

        all_online = all(record["state"] == "ONLINE" for record in indexes)

        if all_online and indexes:
            print("  All vector indexes are ONLINE")
            for record in indexes:
                print(f"    ✓ {record['name']}: {record['state']}")
            return True

        # Show current status
        for record in indexes:
            status = "✓" if record["state"] == "ONLINE" else "○"
            print(f"    {status} {record['name']}: {record['state']}")

        time.sleep(5)

    print(f"  WARNING: Timeout after {timeout}s - some indexes may still be populating")
    return False


def show_schema_summary(session):
    """Display summary of created schema objects."""
    print("\n" + "=" * 60)
    print("SCHEMA SUMMARY")
    print("=" * 60)

    # Count constraints
    result = session.run("SHOW CONSTRAINTS YIELD name RETURN count(*) as count")
    constraint_count = result.single()["count"]
    print(f"Constraints: {constraint_count}")

    # Count indexes by type
    result = session.run("""
        SHOW INDEXES
        YIELD type
        RETURN type, count(*) as count
        ORDER BY type
    """)
    for record in result:
        print(f"{record['type']} indexes: {record['count']}")

    print("=" * 60)


def main():
    """Initialize the V2 schema."""
    print("=" * 60)
    print("HiGraph-CPG Schema V2 Initialization")
    print("=" * 60)

    driver = get_driver()

    try:
        with driver.session() as session:
            # Create schema objects in order
            run_schema_commands(session, CONSTRAINTS, "constraints")
            run_schema_commands(session, PROPERTY_INDEXES, "property indexes")
            run_schema_commands(session, FULLTEXT_INDEXES, "full-text indexes")
            run_schema_commands(session, VECTOR_INDEXES, "vector indexes")

            # Wait for vector indexes
            wait_for_vector_indexes(session)

            # Show summary
            show_schema_summary(session)

        print("\nSchema initialization complete!")

    finally:
        driver.close()


if __name__ == "__main__":
    main()
