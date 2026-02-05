"""
Validate Populated Graph

Runs validation queries against Neo4j to verify node counts, orphan nodes,
relationship completeness, and sample traversals.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.pipeline.config_loader import load_config
from scripts.pipeline.pipeline_context import PipelineContext
from scripts.graph_population.neo4j_client import get_driver


def run(config_path: str):
    """Run graph validation queries."""
    config = load_config(config_path)
    ctx = PipelineContext(config)

    print("=" * 60)
    print("GRAPH VALIDATION")
    print("=" * 60)

    driver = get_driver()
    issues = []

    with driver.session() as session:
        # 1. Node counts
        print("\n1. Node Counts:")
        result = session.run("""
            MATCH (n)
            RETURN labels(n)[0] AS NodeType, count(*) AS Count
            ORDER BY Count DESC
        """)
        node_counts = {}
        for record in result:
            node_type = record['NodeType']
            count = record['Count']
            node_counts[node_type] = count
            print(f"  {node_type}: {count}")

        # Check expected counts
        expected_map = {
            'Recommendation': config.expected_counts.get('recommendations', 0),
            'KeyQuestion': config.expected_counts.get('key_questions', 0),
            'Study': config.expected_counts.get('studies', 0),
            'EvidenceBody': config.expected_counts.get('evidence_bodies', 0),
            'Guideline': 1,
        }
        for node_type, expected in expected_map.items():
            actual = node_counts.get(node_type, 0)
            if actual != expected and expected > 0:
                issues.append(f"{node_type} count mismatch: {actual} (expected {expected})")

        # 2. Relationship counts
        print("\n2. Relationship Counts:")
        result = session.run("""
            MATCH ()-[r]->()
            RETURN type(r) AS RelType, count(*) AS Count
            ORDER BY Count DESC
        """)
        for record in result:
            print(f"  {record['RelType']}: {record['Count']}")

        # 3. Orphaned recommendations (no BASED_ON)
        print("\n3. Orphan Checks:")
        result = session.run("""
            MATCH (r:Recommendation)
            WHERE NOT (r)-[:BASED_ON]->(:EvidenceBody)
            RETURN count(r) AS orphan_count
        """)
        orphan_recs = result.single()['orphan_count']
        print(f"  Recommendations without BASED_ON: {orphan_recs}")
        if orphan_recs > 0:
            issues.append(f"{orphan_recs} recommendations have no BASED_ON relationship")

        # Orphaned KQs (no ANSWERS)
        result = session.run("""
            MATCH (kq:KeyQuestion)
            WHERE NOT (:EvidenceBody)-[:ANSWERS]->(kq)
            RETURN count(kq) AS orphan_count
        """)
        orphan_kqs = result.single()['orphan_count']
        print(f"  KeyQuestions without ANSWERS: {orphan_kqs}")

        # 4. Evidence chain completeness
        print("\n4. Evidence Chain Completeness:")
        result = session.run("""
            MATCH (kq:KeyQuestion)<-[:ANSWERS]-(eb:EvidenceBody)-[:INCLUDES]->(s:Study)
            RETURN count(DISTINCT kq) AS connected_kqs
        """)
        connected = result.single()['connected_kqs']
        print(f"  KQs with complete evidence chains: {connected}/{config.expected_counts.get('key_questions', 0)}")

        # 5. Sample traversal
        print("\n5. Sample Traversal (first recommendation with evidence chain):")
        result = session.run("""
            MATCH (r:Recommendation)-[:BASED_ON]->(eb:EvidenceBody)-[:INCLUDES]->(s:Study)
            RETURN r.rec_id AS rec, r.rec_text AS text, eb.quality_rating AS grade,
                   collect(s.title)[0..3] AS sample_studies
            LIMIT 1
        """)
        record = result.single()
        if record:
            print(f"  Rec: {record['rec']}")
            text = str(record['text'] or '')
            print(f"  Text: {text[:100]}...")
            print(f"  GRADE: {record['grade']}")
            print(f"  Studies: {record['sample_studies']}")
        else:
            print("  No complete evidence chains found")
            issues.append("No evidence chains traversable")

        # 6. Embedding check
        print("\n6. Embedding Status:")
        for label in ['Recommendation', 'KeyQuestion', 'EvidenceBody']:
            result = session.run(f"""
                MATCH (n:{label})
                WITH count(n) AS total, count(n.embedding) AS embedded
                RETURN total, embedded
            """)
            record = result.single()
            total = record['total']
            embedded = record['embedded']
            print(f"  {label}: {embedded}/{total} embedded")

    driver.close()

    # Summary
    print("\n" + "=" * 60)
    if issues:
        print(f"VALIDATION FOUND {len(issues)} ISSUE(S):")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("ALL VALIDATION CHECKS PASSED")
    print("=" * 60)

    # Save report
    report = {
        'guideline': config.slug,
        'status': 'pass' if not issues else 'issues',
        'node_counts': node_counts,
        'issues': issues,
    }
    report_path = ctx.validation_report_path('graph')
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved to {report_path}")

    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Validate populated graph")
    parser.add_argument('--config', required=True, help="Path to guideline YAML config")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
