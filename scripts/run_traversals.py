"""Seed test data and execute example traversal queries against Neo4j.

Seeds the graph with realistic diabetes CPG data, runs all example traversals,
and optionally cleans up afterward.

Usage:
    python scripts/run_traversals.py             # seed + run + keep data
    python scripts/run_traversals.py --cleanup    # seed + run + clean up
"""

import argparse
import json
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

SEED_FILE = PROJECT_ROOT / "scripts" / "seed_test_data.cypher"
TRAVERSALS_FILE = PROJECT_ROOT / "scripts" / "example_traversals.cypher"


def parse_cypher_file(filepath: Path) -> list[tuple[str, str]]:
    """Parse a .cypher file into (label, statement) tuples.

    Extracts block comments (// ===... heading) as labels and groups
    consecutive non-comment lines as statements.
    """
    text = filepath.read_text(encoding="utf-8")
    blocks = []
    current_label = ""
    current_lines = []

    for line in text.splitlines():
        stripped = line.strip()

        # Section header
        if stripped.startswith("// ====="):
            # Save any accumulated statement
            if current_lines:
                stmt = "\n".join(current_lines).strip().rstrip(";")
                if stmt:
                    blocks.append((current_label, stmt))
                current_lines = []
            continue

        # Label comment (e.g., "// TRAVERSAL 1: Evidence Chain")
        if stripped.startswith("// TRAVERSAL") or stripped.startswith("// Clinical Question"):
            current_label = stripped.lstrip("/ ").strip()
            continue

        # Regular comment or blank line
        if stripped.startswith("//") or stripped == "":
            # If we have accumulated lines, a blank after a semicolon means end of statement
            if current_lines:
                combined = "\n".join(current_lines).strip()
                if combined.endswith(";"):
                    stmt = combined.rstrip(";")
                    if stmt:
                        blocks.append((current_label, stmt))
                    current_lines = []
            continue

        current_lines.append(line)

    # Final block
    if current_lines:
        stmt = "\n".join(current_lines).strip().rstrip(";")
        if stmt:
            blocks.append((current_label, stmt))

    return blocks


def parse_seed_statements(filepath: Path) -> list[str]:
    """Parse seed file into individual Cypher statements (split on ; at line end)."""
    text = filepath.read_text(encoding="utf-8")
    statements = []
    current = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("//") or stripped == "":
            continue
        current.append(line)
        if stripped.endswith(";"):
            stmt = "\n".join(current).strip().rstrip(";")
            if stmt:
                statements.append(stmt)
            current = []

    if current:
        stmt = "\n".join(current).strip().rstrip(";")
        if stmt:
            statements.append(stmt)

    return statements


def seed_data(driver):
    """Execute seed_test_data.cypher to populate the graph."""
    # Clear existing data to avoid constraint violations on re-run
    with driver.session() as session:
        result = session.run("MATCH (n) DETACH DELETE n RETURN count(*) AS deleted")
        deleted = result.single()["deleted"]
        if deleted > 0:
            print(f"  Cleared {deleted} existing nodes.")

    print("Seeding test data...")
    statements = parse_seed_statements(SEED_FILE)
    print(f"  {len(statements)} statements to execute")

    with driver.session() as session:
        for i, stmt in enumerate(statements, 1):
            try:
                session.run(stmt)
            except Exception as e:
                display = stmt.replace("\n", " ")[:80]
                print(f"  FAIL [{i}]: {display}...")
                print(f"    Error: {e}")
                raise

    # Verify node counts
    with driver.session() as session:
        result = session.run(
            "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count ORDER BY count DESC"
        )
        print("  Seeded nodes:")
        for record in result:
            print(f"    {record['label']}: {record['count']}")

    print("  Seed complete.\n")


def run_traversals(driver):
    """Execute example_traversals.cypher and display results."""
    blocks = parse_cypher_file(TRAVERSALS_FILE)
    print(f"Running {len(blocks)} traversal queries...\n")

    results = {}

    with driver.session() as session:
        for label, stmt in blocks:
            print(f"--- {label} ---")
            try:
                result = session.run(stmt)
                records = [dict(r) for r in result]

                if records:
                    # Pretty-print first record
                    for record in records:
                        for key, value in record.items():
                            print(f"  {key}: {_format_value(value)}")
                        if len(records) > 1:
                            print(f"  ... ({len(records)} total records)")
                            break
                else:
                    print("  (no results)")

                results[label] = records
                print()

            except Exception as e:
                print(f"  ERROR: {e}\n")
                results[label] = {"error": str(e)}

    return results


def cleanup(driver):
    """Remove all nodes and relationships."""
    print("Cleaning up all data...")
    with driver.session() as session:
        result = session.run("MATCH (n) DETACH DELETE n RETURN count(*) AS deleted")
        count = result.single()["deleted"]
        print(f"  Deleted {count} nodes.\n")


def _format_value(value, indent=4):
    """Format a value for display."""
    if isinstance(value, list):
        if not value:
            return "[]"
        if isinstance(value[0], dict):
            lines = []
            for item in value:
                lines.append(" " * indent + json.dumps(item, default=str))
            return "[\n" + ",\n".join(lines) + "\n" + " " * indent + "]"
        return str(value)
    return str(value)


def main():
    parser = argparse.ArgumentParser(description="Run HiGraph-CPG example traversals")
    parser.add_argument("--cleanup", action="store_true", help="Clean up test data after running")
    parser.add_argument("--seed-only", action="store_true", help="Only seed data, don't run traversals")
    args = parser.parse_args()

    if not NEO4J_PASSWORD:
        print("Error: NEO4J_PASSWORD not set. Check your .env file.")
        sys.exit(1)

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        driver.verify_connectivity()
        print(f"Connected to Neo4j at {NEO4J_URI}\n")
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

    try:
        seed_data(driver)

        if not args.seed_only:
            run_traversals(driver)

        if args.cleanup:
            cleanup(driver)
        else:
            print("Data preserved in Neo4j. Use --cleanup flag to remove.")

    finally:
        driver.close()


if __name__ == "__main__":
    main()
