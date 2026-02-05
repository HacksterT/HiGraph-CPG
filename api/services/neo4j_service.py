"""Neo4j database service with connection pooling."""

import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from neo4j.exceptions import AuthError, ServiceUnavailable

from api.config import Settings, get_settings
from neo4j import Driver, GraphDatabase

# Node type configurations: index name and fields to return
NODE_TYPE_CONFIG = {
    "Recommendation": {
        "index": "recommendation_embedding",
        "return_clause": """
            node.rec_id AS rec_id,
            node.rec_text AS rec_text,
            node.strength AS strength,
            node.direction AS direction,
            node.topic AS topic,
            score AS similarity_score
        """,
    },
    "Study": {
        "index": "study_embedding",
        "return_clause": """
            node.study_id AS study_id,
            node.title AS title,
            node.abstract AS abstract,
            node.authors AS authors,
            node.journal AS journal,
            node.year AS year,
            node.pmid AS pmid,
            node.study_type AS study_type,
            score AS similarity_score
        """,
    },
    "KeyQuestion": {
        "index": "keyquestion_embedding",
        "return_clause": """
            node.kq_id AS kq_id,
            node.question_text AS question_text,
            node.kq_number AS kq_number,
            node.population AS population,
            node.intervention AS intervention,
            score AS similarity_score
        """,
    },
    "EvidenceBody": {
        "index": "evidencebody_embedding",
        "return_clause": """
            node.evidence_id AS evidence_id,
            node.key_findings AS key_findings,
            node.quality_rating AS quality_rating,
            node.num_studies AS num_studies,
            score AS similarity_score
        """,
    },
    "ClinicalModule": {
        "index": "clinicalmodule_embedding",
        "return_clause": """
            node.module_id AS module_id,
            node.module_name AS module_name,
            node.description AS description,
            node.topics AS topics,
            score AS similarity_score
        """,
    },
}


class Neo4jService:
    """Service for Neo4j database operations."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._driver: Driver | None = None

    @property
    def driver(self) -> Driver:
        """Get or create the Neo4j driver (lazy initialization)."""
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self.settings.neo4j_uri,
                auth=(self.settings.neo4j_user, self.settings.neo4j_password),
                max_connection_lifetime=3600,
                max_connection_pool_size=50,
                connection_acquisition_timeout=30,
            )
        return self._driver

    def close(self):
        """Close the driver connection."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def verify_connectivity(self) -> bool:
        """Check if Neo4j is reachable."""
        try:
            self.driver.verify_connectivity()
            return True
        except (ServiceUnavailable, AuthError):
            return False

    @contextmanager
    def session(self) -> Generator:
        """Context manager for Neo4j sessions."""
        session = self.driver.session()
        try:
            yield session
        finally:
            session.close()

    def vector_search_with_embedding(
        self,
        query_text: str,
        node_type: str = "Recommendation",
        top_k: int = 10,
    ) -> tuple[list[dict[str, Any]], int, int]:
        """
        Generate embedding and execute vector search in a single Neo4j call.

        Uses the GenAI plugin to embed the query server-side, avoiding a separate
        OpenAI API call from Python.

        Args:
            query_text: Natural language query
            node_type: Type of node to search (Recommendation, Study, etc.)
            top_k: Number of results to return

        Returns:
            Tuple of (results list, embedding time ms, search time ms)
        """
        if node_type not in NODE_TYPE_CONFIG:
            raise ValueError(f"Unknown node type: {node_type}. Valid types: {list(NODE_TYPE_CONFIG.keys())}")

        config_entry = NODE_TYPE_CONFIG[node_type]
        index_name = config_entry["index"]
        return_clause = config_entry["return_clause"]

        cypher = f"""
        CALL genai.vector.encodeBatch($texts, 'OpenAI', $config) YIELD vector AS queryEmbedding
        WITH queryEmbedding
        CALL db.index.vector.queryNodes($index_name, $top_k, queryEmbedding)
        YIELD node, score
        RETURN {return_clause}
        ORDER BY score DESC
        """

        config = {
            "token": self.settings.openai_api_key,
            "model": self.settings.embedding_model,
        }

        start_time = time.perf_counter()

        with self.session() as session:
            result = session.run(
                cypher,
                texts=[query_text],
                config=config,
                index_name=index_name,
                top_k=top_k,
            )
            records = [dict(record) for record in result]

        total_time_ms = int((time.perf_counter() - start_time) * 1000)

        # Approximate split: embedding typically ~60-70% of total time
        embedding_time_ms = int(total_time_ms * 0.65)
        search_time_ms = total_time_ms - embedding_time_ms

        return records, embedding_time_ms, search_time_ms

    def get_supported_node_types(self) -> list[str]:
        """Return list of supported node types for vector search."""
        return list(NODE_TYPE_CONFIG.keys())

    def execute_graph_query(
        self,
        cypher: str,
        params: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Execute a parameterized Cypher query.

        Args:
            cypher: The Cypher query string
            params: Query parameters

        Returns:
            Tuple of (results list, query time in ms)
        """
        start_time = time.perf_counter()

        with self.session() as session:
            result = session.run(cypher, **params)
            records = [dict(record) for record in result]

        query_time_ms = int((time.perf_counter() - start_time) * 1000)
        return records, query_time_ms


# Singleton instance
_neo4j_service: Neo4jService | None = None


def get_neo4j_service() -> Neo4jService:
    """Get the singleton Neo4j service instance."""
    global _neo4j_service
    if _neo4j_service is None:
        _neo4j_service = Neo4jService(get_settings())
    return _neo4j_service
