"""Initialize the Neo4j schema for HiGraph-CPG.

Executes constraints, indexes, and vector indexes against a running Neo4j instance.
Reads connection credentials from .env file.

Usage:
    python scripts/init_schema.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

SCHEMA_DIR = PROJECT_ROOT / "schema"

CYPHER_FILES = [
    "constraints.cypher",
    "indexes.cypher",
    "vector_indexes.cypher",
]


def parse_cypher_statements(filepath: Path) -> list[str]:
    """Parse a .cypher file into individual statements, ignoring comments."""
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
    # Handle statement without trailing semicolon
    if current:
        stmt = "\n".join(current).strip().rstrip(";")
        if stmt:
            statements.append(stmt)
    return statements


def execute_schema_file(driver, filepath: Path) -> tuple[int, int]:
    """Execute all statements in a cypher file. Returns (success_count, failure_count)."""
    statements = parse_cypher_statements(filepath)
    successes = 0
    failures = 0

    print(f"\n--- {filepath.name} ({len(statements)} statements) ---")

    for stmt in statements:
        # Truncate display for readability
        display = stmt.replace("\n", " ")
        if len(display) > 100:
            display = display[:97] + "..."
        try:
            with driver.session() as session:
                session.run(stmt)
            print(f"  OK: {display}")
            successes += 1
        except Exception as e:
            print(f"  FAIL: {display}")
            print(f"        Error: {e}")
            failures += 1

    return successes, failures


def verify_schema(driver):
    """Verify constraints and indexes were created."""
    print("\n--- Verification ---")

    with driver.session() as session:
        # Count constraints
        result = session.run("SHOW CONSTRAINTS")
        constraints = list(result)
        print(f"  Constraints: {len(constraints)}")
        for c in constraints:
            print(f"    - {c['name']} ({c['type']})")

        # Count indexes
        result = session.run("SHOW INDEXES")
        indexes = list(result)
        print(f"  Indexes: {len(indexes)}")
        for idx in indexes:
            print(f"    - {idx['name']} ({idx['type']}, state={idx['state']})")


def main():
    if not NEO4J_PASSWORD:
        print("Error: NEO4J_PASSWORD not set. Check your .env file.")
        sys.exit(1)

    print(f"Connecting to Neo4j at {NEO4J_URI} as {NEO4J_USER}...")

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        driver.verify_connectivity()
        print("Connected successfully.")
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

    total_successes = 0
    total_failures = 0

    for filename in CYPHER_FILES:
        filepath = SCHEMA_DIR / filename
        if not filepath.exists():
            print(f"\nWARNING: {filepath} not found, skipping.")
            continue
        s, f = execute_schema_file(driver, filepath)
        total_successes += s
        total_failures += f

    verify_schema(driver)

    print(f"\n=== Summary: {total_successes} succeeded, {total_failures} failed ===")

    driver.close()

    if total_failures > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
