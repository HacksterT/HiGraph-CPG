"""Pytest-based tests for HiGraph-CPG graph traversal patterns.

Seeds the Neo4j database with test data, runs traversal queries,
and asserts expected results. Cleans up after all tests complete.

Requires:
    - Running Neo4j instance (docker-compose up -d)
    - Schema initialized (python scripts/init_schema.py)
    - NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD in .env

Usage:
    pytest tests/test_traversals.py -v
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from neo4j import GraphDatabase

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

SEED_FILE = PROJECT_ROOT / "scripts" / "seed_test_data.cypher"


def parse_seed_statements(filepath: Path) -> list[str]:
    """Parse seed file into individual Cypher statements."""
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


@pytest.fixture(scope="module")
def driver():
    """Create a Neo4j driver for the test module."""
    if not NEO4J_PASSWORD:
        pytest.skip("NEO4J_PASSWORD not set")
    d = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        d.verify_connectivity()
    except Exception:
        pytest.skip("Neo4j not available")
    yield d
    d.close()


@pytest.fixture(scope="module", autouse=True)
def seed_and_cleanup(driver):
    """Seed test data before tests, clean up after."""
    # Clean any existing data
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")

    # Seed
    statements = parse_seed_statements(SEED_FILE)
    with driver.session() as session:
        for stmt in statements:
            session.run(stmt)

    yield

    # Cleanup
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")


class TestEvidenceChain:
    """Traversal 1: Recommendation -> EvidenceBody -> Studies"""

    def test_metformin_recommendation_has_evidence(self, driver):
        with driver.session() as session:
            result = session.run("""
                MATCH (r:Recommendation {rec_id: 'REC_008'})
                -[:BASED_ON]->(eb:EvidenceBody)
                -[:INCLUDES]->(s:Study)
                RETURN r.rec_text AS rec_text,
                       eb.quality_rating AS quality,
                       collect(s.study_id) AS study_ids
            """)
            record = result.single()
            assert record is not None
            assert "metformin" in record["rec_text"].lower()
            assert record["quality"] == "High"
            assert "STUDY_UKPDS34" in record["study_ids"]

    def test_glp1ra_recommendation_has_multiple_studies(self, driver):
        with driver.session() as session:
            result = session.run("""
                MATCH (r:Recommendation {rec_id: 'REC_015'})
                -[:BASED_ON]->(eb:EvidenceBody)
                -[:INCLUDES]->(s:Study)
                RETURN collect(s.study_id) AS study_ids
            """)
            record = result.single()
            assert record is not None
            study_ids = record["study_ids"]
            assert len(study_ids) >= 2
            assert "STUDY_LEADER" in study_ids
            assert "STUDY_EMPAREG" in study_ids


class TestClinicalDecisionSupport:
    """Traversal 2: ClinicalScenario -> Recommendations -> Interventions"""

    def test_new_diagnosis_triggers_recommendations(self, driver):
        with driver.session() as session:
            result = session.run("""
                MATCH (cs:ClinicalScenario {scenario_id: 'CS_NEWDX_T2DM'})
                -[t:TRIGGERS]->(r:Recommendation)
                WHERE r.status = 'Active'
                RETURN collect(r.rec_id) AS rec_ids,
                       collect(t.priority) AS priorities
            """)
            record = result.single()
            assert record is not None
            rec_ids = record["rec_ids"]
            assert "REC_008" in rec_ids
            assert "REC_007" in rec_ids

    def test_ascvd_scenario_triggers_glp1ra(self, driver):
        with driver.session() as session:
            result = session.run("""
                MATCH (cs:ClinicalScenario {scenario_id: 'CS_T2DM_ASCVD'})
                -[t:TRIGGERS]->(r:Recommendation)
                -[:RECOMMENDS]->(i:Intervention)
                WHERE r.status = 'Active'
                RETURN collect(DISTINCT i.name) AS interventions
            """)
            record = result.single()
            assert record is not None
            assert "GLP-1 Receptor Agonist" in record["interventions"]


class TestBenefitHarmAnalysis:
    """Traversal 3: Intervention -> Benefits + AdverseEvents"""

    def test_metformin_has_benefits_and_harms(self, driver):
        with driver.session() as session:
            result = session.run("""
                MATCH (i:Intervention {intervention_id: 'INT_METFORMIN'})
                OPTIONAL MATCH (i)-[:PRODUCES]->(b:Benefit)
                OPTIONAL MATCH (i)-[:CAUSES]->(ae:AdverseEvent)
                RETURN collect(DISTINCT b.name) AS benefits,
                       collect(DISTINCT ae.name) AS adverse_events
            """)
            record = result.single()
            assert record is not None
            assert "HbA1c reduction" in record["benefits"]
            assert "Weight neutral or loss" in record["benefits"]
            assert "Gastrointestinal side effects" in record["adverse_events"]
            assert "Lactic acidosis" in record["adverse_events"]


class TestContraindicationCheck:
    """Traversal 4: PatientCharacteristic -> Contraindication -> Intervention"""

    def test_renal_impairment_contraindicates_metformin(self, driver):
        with driver.session() as session:
            result = session.run("""
                MATCH (pc:PatientCharacteristic {characteristic_id: 'PC_RENAL_SEVERE'})
                <-[:APPLIES_TO]-(ci:Contraindication)
                -[:CONTRAINDICATES]->(i:Intervention)
                RETURN collect({
                    intervention: i.name,
                    type: ci.type,
                    severity: ci.severity
                }) AS contraindications
            """)
            record = result.single()
            assert record is not None
            contraindications = record["contraindications"]
            assert len(contraindications) >= 1

            metformin_ci = [c for c in contraindications if c["intervention"] == "Metformin"]
            assert len(metformin_ci) == 1
            assert metformin_ci[0]["type"] == "Absolute"
            assert metformin_ci[0]["severity"] == "Critical"


class TestVersionHistory:
    """Traversal 5: Recommendation versioning via SUPERSEDES"""

    def test_recommendation_supersedes_chain(self, driver):
        with driver.session() as session:
            result = session.run("""
                MATCH path = (current:Recommendation {rec_id: 'REC_008'})
                -[:SUPERSEDES*1..]->(old:Recommendation)
                RETURN old.rec_id AS old_id,
                       old.version AS old_version,
                       old.status AS old_status
            """)
            record = result.single()
            assert record is not None
            assert record["old_id"] == "REC_008_v5"
            assert record["old_version"] == "5.0"
            assert record["old_status"] == "Superseded"


class TestDecisionFramework:
    """Traversal 6: GRADE Decision Framework reasoning"""

    def test_dsme_recommendation_has_framework(self, driver):
        with driver.session() as session:
            result = session.run("""
                MATCH (r:Recommendation {rec_id: 'REC_007'})
                <-[:DETERMINES]-(df:DecisionFramework)
                RETURN df.confidence_in_evidence AS confidence,
                       df.balance_of_outcomes AS balance,
                       df.overall_judgment AS judgment
            """)
            record = result.single()
            assert record is not None
            assert record["confidence"] == "Moderate"
            assert "Benefits outweigh harms" in record["balance"]
            assert "Strong For" in record["judgment"]

    def test_metformin_framework_weighs_benefits_and_harms(self, driver):
        with driver.session() as session:
            result = session.run("""
                MATCH (df:DecisionFramework {framework_id: 'DF_008'})
                -[:WEIGHS]->(target)
                RETURN labels(target)[0] AS type, target.name AS name
            """)
            records = list(result)
            types = {r["type"] for r in records}
            names = {r["name"] for r in records}
            assert "Benefit" in types
            assert "AdverseEvent" in types
            assert "HbA1c reduction" in names


class TestMultiHopTraversal:
    """Traversal 7: Study -> EvidenceBody -> Recommendation -> ClinicalScenario"""

    def test_ukpds_traces_to_clinical_scenarios(self, driver):
        with driver.session() as session:
            result = session.run("""
                MATCH (s:Study {study_id: 'STUDY_UKPDS34'})
                <-[:INCLUDES]-(eb:EvidenceBody)
                -[:SUPPORTS]->(r:Recommendation)
                <-[:TRIGGERS]-(cs:ClinicalScenario)
                WHERE r.status = 'Active'
                RETURN s.title AS study,
                       r.rec_id AS rec_id,
                       collect(DISTINCT cs.scenario_id) AS scenarios
            """)
            record = result.single()
            assert record is not None
            assert record["rec_id"] == "REC_008"
            assert "CS_NEWDX_T2DM" in record["scenarios"]
