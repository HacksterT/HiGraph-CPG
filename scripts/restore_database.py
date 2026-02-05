"""
Neo4j Database Restore Script

Restores nodes and relationships from backup JSON files.
After restore, run generate_embeddings.py to regenerate embeddings.

Usage:
    .venv/Scripts/python.exe scripts/restore_database.py --input-dir backups/20260205_143000
    .venv/Scripts/python.exe scripts/restore_database.py --input-dir backups/20260205_143000 --clear-first
"""

import json
import os
import sys
from pathlib import Path

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


# Node label to ID property mapping
NODE_ID_PROPERTIES = {
    "Guideline": "guideline_id",
    "ClinicalModule": "module_id",
    "CarePhase": "phase_id",
    "Recommendation": "rec_id",
    "KeyQuestion": "kq_id",
    "EvidenceBody": "eb_id",
    "Study": "study_id",
    "Intervention": "intervention_id",
    "Condition": "condition_id",
}


def clear_database(session):
    """Delete all nodes and relationships."""
    print("Clearing database...")
    session.run("MATCH (n) DETACH DELETE n")
    print("  Database cleared")


def restore_nodes(session, label: str, nodes: list):
    """Restore nodes of a given type."""
    if not nodes:
        return 0

    id_prop = NODE_ID_PROPERTIES.get(label)
    if not id_prop:
        print(f"  WARNING: Unknown label {label}, skipping")
        return 0

    count = 0
    for node in nodes:
        id_value = node.get(id_prop)
        if not id_value:
            continue

        # Build SET clause
        set_parts = []
        params = {"id_value": id_value}
        for key, value in node.items():
            if key == id_prop:
                continue
            param_name = f"p_{key}"
            set_parts.append(f"n.{key} = ${param_name}")
            params[param_name] = value

        set_clause = ", ".join(set_parts) if set_parts else "n.placeholder = null"

        query = f"""
        MERGE (n:{label} {{{id_prop}: $id_value}})
        SET {set_clause}
        """
        session.run(query, params)
        count += 1

    return count


def restore_relationships(session, rels: list):
    """Restore relationships."""
    count = 0
    for rel in rels:
        from_label = rel["from_label"]
        from_id = rel["from_id"]
        to_label = rel["to_label"]
        to_id = rel["to_id"]
        rel_type = rel["rel_type"]
        rel_props = rel.get("rel_props") or {}

        from_id_prop = NODE_ID_PROPERTIES.get(from_label)
        to_id_prop = NODE_ID_PROPERTIES.get(to_label)

        if not from_id_prop or not to_id_prop:
            continue

        params = {"from_id": from_id, "to_id": to_id}

        if rel_props:
            set_parts = []
            for key, value in rel_props.items():
                param_name = f"rp_{key}"
                set_parts.append(f"r.{key} = ${param_name}")
                params[param_name] = value
            set_clause = "SET " + ", ".join(set_parts)
        else:
            set_clause = ""

        query = f"""
        MATCH (a:{from_label} {{{from_id_prop}: $from_id}})
        MATCH (b:{to_label} {{{to_id_prop}: $to_id}})
        MERGE (a)-[r:{rel_type}]->(b)
        {set_clause}
        """
        session.run(query, params)
        count += 1

    return count


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Restore Neo4j database from JSON backup")
    parser.add_argument('--input-dir', required=True, help="Backup directory to restore from")
    parser.add_argument('--clear-first', action='store_true', help="Clear database before restore")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        print(f"ERROR: Backup directory not found: {input_dir}")
        sys.exit(1)

    # Load summary if available
    summary_file = input_dir / "backup_summary.json"
    if summary_file.exists():
        with open(summary_file) as f:
            summary = json.load(f)
        print(f"Restoring backup from: {summary.get('backup_timestamp', 'unknown')}")
        print(f"Expected: {summary.get('total_nodes', '?')} nodes, {summary.get('total_relationships', '?')} relationships")
    else:
        print(f"Restoring from: {input_dir}")

    print("=" * 60)

    driver = get_driver()

    try:
        with driver.session() as session:
            if args.clear_first:
                clear_database(session)

            # Find and restore node files
            print("\nRestoring nodes...")
            total_nodes = 0
            for node_file in input_dir.glob("*_nodes.json"):
                label = node_file.stem.replace("_nodes", "").title()
                # Handle special cases
                label_map = {
                    "Clinicalmodule": "ClinicalModule",
                    "Carephase": "CarePhase",
                    "Keyquestion": "KeyQuestion",
                    "Evidencebody": "EvidenceBody",
                }
                label = label_map.get(label, label)

                with open(node_file) as f:
                    nodes = json.load(f)

                count = restore_nodes(session, label, nodes)
                print(f"  {label}: {count} nodes")
                total_nodes += count

            # Restore relationships
            rel_file = input_dir / "relationships.json"
            if rel_file.exists():
                print("\nRestoring relationships...")
                with open(rel_file) as f:
                    rels = json.load(f)
                count = restore_relationships(session, rels)
                print(f"  {count} relationships restored")

            print("\n" + "=" * 60)
            print("RESTORE COMPLETE")
            print("=" * 60)
            print(f"Total nodes restored: {total_nodes}")
            print("\nNEXT STEP: Regenerate embeddings:")
            print("  .venv/Scripts/python.exe scripts/graph_population/generate_embeddings.py --config configs/guidelines/diabetes-t2-2023.yaml")

    finally:
        driver.close()


if __name__ == "__main__":
    main()
