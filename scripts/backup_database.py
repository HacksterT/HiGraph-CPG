"""
Neo4j Database Backup Script

Exports all nodes and relationships to JSON files for backup and recovery.
Does NOT export embeddings (they can be regenerated cheaply ~$0.01).

Usage:
    .venv/Scripts/python.exe scripts/backup_database.py
    .venv/Scripts/python.exe scripts/backup_database.py --output-dir backups/2026-02-05
"""

import json
import os
import sys
from datetime import datetime
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


def export_nodes(session, label: str) -> list:
    """Export all nodes of a given label (excluding embeddings)."""
    result = session.run(f"""
        MATCH (n:{label})
        RETURN n
    """)

    nodes = []
    for record in result:
        node = dict(record["n"])
        # Remove embedding to keep backup small (can regenerate)
        node.pop("embedding", None)
        nodes.append(node)

    return nodes


def export_relationships(session) -> list:
    """Export all relationships with their endpoints."""
    result = session.run("""
        MATCH (a)-[r]->(b)
        RETURN
            labels(a)[0] AS from_label,
            keys(a)[0] AS from_key,
            a[keys(a)[0]] AS from_id,
            type(r) AS rel_type,
            properties(r) AS rel_props,
            labels(b)[0] AS to_label,
            keys(b)[0] AS to_key,
            b[keys(b)[0]] AS to_id
    """)

    rels = []
    for record in result:
        rels.append({
            "from_label": record["from_label"],
            "from_id": record["from_id"],
            "rel_type": record["rel_type"],
            "rel_props": dict(record["rel_props"]) if record["rel_props"] else None,
            "to_label": record["to_label"],
            "to_id": record["to_id"],
        })

    return rels


def get_node_labels(session) -> list:
    """Get all node labels in the database."""
    result = session.run("CALL db.labels()")
    return [record["label"] for record in result]


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Backup Neo4j database to JSON")
    parser.add_argument('--output-dir', default=None, help="Output directory (default: backups/<timestamp>)")
    args = parser.parse_args()

    # Create output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("backups") / timestamp

    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("HiGraph-CPG Database Backup")
    print("=" * 60)
    print(f"Output directory: {output_dir}")

    driver = get_driver()

    try:
        with driver.session() as session:
            # Get all labels
            labels = get_node_labels(session)
            print(f"\nFound {len(labels)} node types: {', '.join(labels)}")

            # Export each node type
            print("\nExporting nodes...")
            summary = {}
            for label in labels:
                nodes = export_nodes(session, label)
                if nodes:
                    output_file = output_dir / f"{label.lower()}_nodes.json"
                    with open(output_file, 'w') as f:
                        json.dump(nodes, f, indent=2, default=str)
                    print(f"  {label}: {len(nodes)} nodes -> {output_file.name}")
                    summary[label] = len(nodes)

            # Export relationships
            print("\nExporting relationships...")
            rels = export_relationships(session)
            output_file = output_dir / "relationships.json"
            with open(output_file, 'w') as f:
                json.dump(rels, f, indent=2, default=str)
            print(f"  {len(rels)} relationships -> {output_file.name}")

            # Write summary
            summary_data = {
                "backup_timestamp": datetime.now().isoformat(),
                "node_counts": summary,
                "total_nodes": sum(summary.values()),
                "total_relationships": len(rels),
                "note": "Embeddings excluded - regenerate with generate_embeddings.py (~$0.01)"
            }
            summary_file = output_dir / "backup_summary.json"
            with open(summary_file, 'w') as f:
                json.dump(summary_data, f, indent=2)

            print("\n" + "=" * 60)
            print("BACKUP SUMMARY")
            print("=" * 60)
            print(f"Total nodes: {summary_data['total_nodes']}")
            print(f"Total relationships: {summary_data['total_relationships']}")
            print(f"Output: {output_dir}")
            print("\nTo restore: python scripts/restore_database.py --input-dir " + str(output_dir))

    finally:
        driver.close()


if __name__ == "__main__":
    main()
