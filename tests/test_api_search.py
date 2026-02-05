"""Tests for the vector search API endpoint."""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_ok(self, client):
        """Health check should return status ok when Neo4j is connected."""
        response = client.get("/health")
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "ok"
            assert data["neo4j"] == "connected"
            assert "version" in data


class TestVectorSearchEndpoint:
    """Tests for POST /api/v1/search/vector endpoint."""

    def test_valid_recommendation_search(self, client):
        """Valid search query should return ranked Recommendation results."""
        response = client.post(
            "/api/v1/search/vector",
            json={"query": "diabetes medications", "top_k": 5, "node_type": "Recommendation"}
        )

        if response.status_code == 503:
            pytest.skip("Neo4j not available")

        assert response.status_code == 200
        data = response.json()

        assert "results" in data
        assert "reasoning" in data
        assert len(data["results"]) <= 5

        # Check result structure for Recommendation
        if data["results"]:
            result = data["results"][0]
            assert result["node_type"] == "Recommendation"
            assert "rec_id" in result
            assert "rec_text" in result
            assert "similarity_score" in result
            assert 0 <= result["similarity_score"] <= 1

        # Check reasoning structure
        reasoning = data["reasoning"]
        assert reasoning["path_used"] == "vector"
        assert reasoning["node_type_searched"] == "Recommendation"

    def test_valid_study_search(self, client):
        """Valid Study search should return study results with abstracts."""
        response = client.post(
            "/api/v1/search/vector",
            json={"query": "SGLT2 cardiovascular", "top_k": 3, "node_type": "Study"}
        )

        if response.status_code == 503:
            pytest.skip("Neo4j not available")

        assert response.status_code == 200
        data = response.json()

        if data["results"]:
            result = data["results"][0]
            assert result["node_type"] == "Study"
            assert "study_id" in result
            assert "title" in result
            assert "similarity_score" in result

    def test_valid_keyquestion_search(self, client):
        """Valid KeyQuestion search should return KQ results."""
        response = client.post(
            "/api/v1/search/vector",
            json={"query": "glycemic targets", "top_k": 2, "node_type": "KeyQuestion"}
        )

        if response.status_code == 503:
            pytest.skip("Neo4j not available")

        assert response.status_code == 200
        data = response.json()

        if data["results"]:
            result = data["results"][0]
            assert result["node_type"] == "KeyQuestion"
            assert "kq_id" in result
            assert "question_text" in result

    def test_valid_evidencebody_search(self, client):
        """Valid EvidenceBody search should return evidence results."""
        response = client.post(
            "/api/v1/search/vector",
            json={"query": "cardiovascular outcomes", "top_k": 2, "node_type": "EvidenceBody"}
        )

        if response.status_code == 503:
            pytest.skip("Neo4j not available")

        assert response.status_code == 200
        data = response.json()

        if data["results"]:
            result = data["results"][0]
            assert result["node_type"] == "EvidenceBody"
            assert "evidence_id" in result
            assert "key_findings" in result

    def test_valid_clinicalmodule_search(self, client):
        """Valid ClinicalModule search should return module results."""
        response = client.post(
            "/api/v1/search/vector",
            json={"query": "pharmacotherapy drugs", "top_k": 2, "node_type": "ClinicalModule"}
        )

        if response.status_code == 503:
            pytest.skip("Neo4j not available")

        assert response.status_code == 200
        data = response.json()

        if data["results"]:
            result = data["results"][0]
            assert result["node_type"] == "ClinicalModule"
            assert "module_id" in result
            assert "module_name" in result

    def test_empty_query_returns_422(self, client):
        """Empty query should return 422 validation error."""
        response = client.post(
            "/api/v1/search/vector",
            json={"query": "", "top_k": 5}
        )
        assert response.status_code == 422
        assert "string_too_short" in response.text

    def test_missing_query_returns_422(self, client):
        """Missing query field should return 422 validation error."""
        response = client.post(
            "/api/v1/search/vector",
            json={"top_k": 5}
        )
        assert response.status_code == 422
        assert "missing" in response.text

    def test_top_k_too_high_returns_422(self, client):
        """top_k > 50 should return 422 validation error."""
        response = client.post(
            "/api/v1/search/vector",
            json={"query": "diabetes", "top_k": 100}
        )
        assert response.status_code == 422
        assert "less_than_equal" in response.text

    def test_top_k_too_low_returns_422(self, client):
        """top_k < 1 should return 422 validation error."""
        response = client.post(
            "/api/v1/search/vector",
            json={"query": "diabetes", "top_k": 0}
        )
        assert response.status_code == 422

    def test_invalid_node_type_returns_422(self, client):
        """Invalid node_type should return 422."""
        response = client.post(
            "/api/v1/search/vector",
            json={"query": "diabetes", "node_type": "InvalidType"}
        )
        assert response.status_code == 422

    def test_default_node_type_is_recommendation(self, client):
        """Default node_type should be Recommendation."""
        response = client.post(
            "/api/v1/search/vector",
            json={"query": "diabetes medications", "top_k": 3}
        )

        if response.status_code == 503:
            pytest.skip("Neo4j not available")

        assert response.status_code == 200
        data = response.json()
        assert data["reasoning"]["node_type_searched"] == "Recommendation"

    def test_search_returns_relevant_results(self, client):
        """Search for kidney disease should return CKD-related recommendations."""
        response = client.post(
            "/api/v1/search/vector",
            json={"query": "chronic kidney disease CKD medications", "top_k": 3}
        )

        if response.status_code == 503:
            pytest.skip("Neo4j not available")

        assert response.status_code == 200
        data = response.json()

        # Should find recommendations about CKD
        rec_texts = [r["rec_text"].lower() for r in data["results"]]
        assert any("kidney" in text or "ckd" in text or "renal" in text for text in rec_texts)


class TestNodeTypesEndpoint:
    """Tests for GET /api/v1/search/node-types endpoint."""

    def test_list_node_types(self, client):
        """Should return list of supported node types."""
        response = client.get("/api/v1/search/node-types")
        assert response.status_code == 200
        data = response.json()
        assert "node_types" in data
        assert "Recommendation" in data["node_types"]
        assert "Study" in data["node_types"]
        assert data["default"] == "Recommendation"


class TestRootEndpoint:
    """Tests for / root endpoint."""

    def test_root_returns_api_info(self, client):
        """Root endpoint should return API information."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "docs" in data


# ============================================================
# STORY-02: Graph Search Tests
# ============================================================


class TestGraphSearchEndpoint:
    """Tests for POST /api/v1/search/graph endpoint."""

    def test_recommendation_only_template(self, client):
        """recommendation_only template should return recommendations by ID."""
        response = client.post(
            "/api/v1/search/graph",
            json={
                "template": "recommendation_only",
                "params": {"rec_ids": ["REC_001", "REC_022"]}
            }
        )

        if response.status_code == 503:
            pytest.skip("Neo4j not available")

        assert response.status_code == 200
        data = response.json()

        assert "results" in data
        assert "reasoning" in data
        assert data["reasoning"]["template_used"] == "recommendation_only"

    def test_recommendation_with_evidence_template(self, client):
        """recommendation_with_evidence template should return recs with evidence info."""
        response = client.post(
            "/api/v1/search/graph",
            json={
                "template": "recommendation_with_evidence",
                "params": {"rec_ids": ["REC_022"]}
            }
        )

        if response.status_code == 503:
            pytest.skip("Neo4j not available")

        assert response.status_code == 200
        data = response.json()

        assert "results" in data
        # Check that evidence fields could be present
        if data["results"]:
            result = data["results"][0]
            assert "rec_id" in result

    def test_evidence_chain_full_template(self, client):
        """evidence_chain_full template should trace from rec to studies."""
        response = client.post(
            "/api/v1/search/graph",
            json={
                "template": "evidence_chain_full",
                "params": {"rec_ids": ["REC_022"]}  # Note: expects list, not single string
            }
        )

        if response.status_code == 503:
            pytest.skip("Neo4j not available")

        assert response.status_code == 200
        data = response.json()

        assert "results" in data
        # This template returns aggregated results with nested evidence and studies
        if data["results"]:
            result = data["results"][0]
            assert "rec_id" in result

    def test_studies_for_recommendation_template(self, client):
        """studies_for_recommendation template should return supporting studies."""
        response = client.post(
            "/api/v1/search/graph",
            json={
                "template": "studies_for_recommendation",
                "params": {"rec_id": "REC_022"}
            }
        )

        if response.status_code == 503:
            pytest.skip("Neo4j not available")

        assert response.status_code == 200
        data = response.json()

        assert "results" in data
        if data["results"]:
            result = data["results"][0]
            assert "study_id" in result

    def test_recommendations_by_topic_template(self, client):
        """recommendations_by_topic template should filter by topic."""
        response = client.post(
            "/api/v1/search/graph",
            json={
                "template": "recommendations_by_topic",
                "params": {"topic": "Pharmacotherapy"}
            }
        )

        if response.status_code == 503:
            pytest.skip("Neo4j not available")

        assert response.status_code == 200
        data = response.json()

        assert "results" in data
        # Template uses CONTAINS for partial match on topic OR subtopic
        for result in data["results"]:
            topic = (result.get("topic") or "").lower()
            subtopic = (result.get("subtopic") or "").lower()
            assert "pharmacotherapy" in topic or "pharmacotherapy" in subtopic

    def test_unknown_template_returns_400(self, client):
        """Unknown template should return 400 error."""
        response = client.post(
            "/api/v1/search/graph",
            json={
                "template": "nonexistent_template",
                "params": {}
            }
        )
        assert response.status_code == 400
        assert "Unknown template" in response.json()["detail"]

    def test_missing_required_param_returns_422(self, client):
        """Missing required parameter should return 422."""
        response = client.post(
            "/api/v1/search/graph",
            json={
                "template": "evidence_chain_full",
                "params": {}  # Missing required 'rec_id'
            }
        )
        assert response.status_code == 422
        assert "rec_id" in response.json()["detail"]

    def test_empty_results_valid_response(self, client):
        """Query with no matches should return empty results, not error."""
        response = client.post(
            "/api/v1/search/graph",
            json={
                "template": "recommendation_only",
                "params": {"rec_ids": ["NONEXISTENT_REC_999"]}
            }
        )

        if response.status_code == 503:
            pytest.skip("Neo4j not available")

        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []
        assert data["reasoning"]["results_count"] == 0


class TestGraphTemplatesEndpoint:
    """Tests for GET /api/v1/search/templates endpoint."""

    def test_list_templates(self, client):
        """Should return list of available templates with their parameters."""
        response = client.get("/api/v1/search/templates")
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) >= 5  # We have 5 templates

        # Check template structure
        template_names = [t["name"] for t in data]
        assert "recommendation_only" in template_names
        assert "evidence_chain_full" in template_names

        # Check a template has required fields
        rec_only = next(t for t in data if t["name"] == "recommendation_only")
        assert "description" in rec_only
        assert "params" in rec_only
        assert any(p["name"] == "rec_ids" for p in rec_only["params"])
