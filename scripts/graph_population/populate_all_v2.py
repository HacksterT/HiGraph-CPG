"""
Populate All V2 Data

Master script that runs all V2 population scripts in the correct order.
Use this to populate the database with the complete V2 schema data.

Usage:
    .venv/Scripts/python.exe scripts/graph_population/populate_all_v2.py --config configs/guidelines/diabetes-t2-2023.yaml
    .venv/Scripts/python.exe scripts/graph_population/populate_all_v2.py --config configs/guidelines/diabetes-t2-2023.yaml --clear-first
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv
load_dotenv()


def clear_database():
    """Clear all nodes and relationships from database."""
    from scripts.graph_population.neo4j_client import get_driver

    print("\n" + "=" * 60)
    print("CLEARING DATABASE")
    print("=" * 60)

    driver = get_driver()
    with driver.session() as session:
        # Count before
        result = session.run("MATCH (n) RETURN count(n) as count")
        before_count = result.single()["count"]
        print(f"Nodes before: {before_count}")

        # Clear
        session.run("MATCH (n) DETACH DELETE n")

        # Count after
        result = session.run("MATCH (n) RETURN count(n) as count")
        after_count = result.single()["count"]
        print(f"Nodes after: {after_count}")

    driver.close()
    print("Database cleared.\n")


def run_step(name: str, module_name: str, config_path: str):
    """Run a single population step."""
    print(f"\n{'='*60}")
    print(f"STEP: {name}")
    print(f"{'='*60}")

    import importlib
    module = importlib.import_module(f"scripts.graph_population.{module_name}")
    module.run(config_path)


def verify_database():
    """Verify database state after population."""
    from scripts.graph_population.neo4j_client import get_driver

    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)

    driver = get_driver()
    with driver.session() as session:
        # Node counts
        result = session.run("""
            MATCH (n)
            RETURN labels(n)[0] AS label, count(*) AS count
            ORDER BY count DESC
        """)
        print("\nNode counts:")
        total_nodes = 0
        for record in result:
            print(f"  {record['label']}: {record['count']}")
            total_nodes += record["count"]
        print(f"  TOTAL: {total_nodes}")

        # Relationship counts
        result = session.run("""
            MATCH ()-[r]->()
            RETURN type(r) AS rel_type, count(*) AS count
            ORDER BY count DESC
        """)
        print("\nRelationship counts:")
        total_rels = 0
        for record in result:
            print(f"  {record['rel_type']}: {record['count']}")
            total_rels += record["count"]
        print(f"  TOTAL: {total_rels}")

    driver.close()
    return total_nodes, total_rels


def main():
    parser = argparse.ArgumentParser(description="Populate all V2 data")
    parser.add_argument("--config", required=True, help="Path to guideline YAML config")
    parser.add_argument("--clear-first", action="store_true", help="Clear database before population")
    parser.add_argument("--skip-existing", action="store_true", help="Skip if data already exists (use MERGE)")
    args = parser.parse_args()

    print("=" * 60)
    print("HiGraph-CPG V2 Full Population")
    print("=" * 60)
    print(f"Config: {args.config}")

    # Optionally clear database
    if args.clear_first:
        clear_database()

    # Population order matters - nodes first, then relationships

    # 1. Core nodes (no dependencies)
    run_step("Guideline", "populate_guideline", args.config)
    run_step("Care Phases (V2)", "populate_care_phases_v2", args.config)
    run_step("Conditions (V2)", "populate_conditions_v2", args.config)
    run_step("Interventions (V2)", "populate_interventions_v2", args.config)

    # 2. Clinical modules (depends on Guideline)
    run_step("Clinical Modules", "populate_clinical_modules", args.config)

    # 3. Evidence chain nodes
    run_step("Key Questions", "populate_key_questions", args.config)
    run_step("Evidence Bodies", "populate_evidence_bodies", args.config)
    run_step("Studies", "populate_studies", args.config)

    # 4. Recommendations (depends on CarePhase)
    run_step("Recommendations", "populate_recommendations", args.config)

    # 5. All relationships (depends on all nodes existing)
    run_step("Original Relationships", "populate_relationships", args.config)
    run_step("V2 Relationships", "populate_relationships_v2", args.config)

    # Verify
    total_nodes, total_rels = verify_database()

    print("\n" + "=" * 60)
    print("POPULATION COMPLETE")
    print("=" * 60)
    print(f"Total nodes: {total_nodes}")
    print(f"Total relationships: {total_rels}")
    print("\nNext step: Generate embeddings")
    print(f"  .venv/Scripts/python.exe scripts/graph_population/generate_embeddings.py --config {args.config}")


if __name__ == "__main__":
    main()
