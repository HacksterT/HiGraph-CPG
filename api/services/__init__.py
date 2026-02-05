"""Service modules for API business logic."""

from api.services.embedding_service import EmbeddingService, get_embedding_service
from api.services.fusion import (
    normalize_graph_results,
    normalize_vector_results,
    reciprocal_rank_fusion,
)
from api.services.graph_templates import (
    TEMPLATES,
    GraphTemplate,
    TemplateParam,
    get_template,
    list_templates,
    validate_params,
)
from api.services.neo4j_service import Neo4jService, get_neo4j_service
from api.services.query_router import QueryRouter, get_query_router
from api.services.reranker import (
    apply_topic_relevance_boost,
    rerank_results,
)

__all__ = [
    "Neo4jService",
    "get_neo4j_service",
    "EmbeddingService",
    "get_embedding_service",
    "GraphTemplate",
    "TemplateParam",
    "TEMPLATES",
    "get_template",
    "list_templates",
    "validate_params",
    "QueryRouter",
    "get_query_router",
    "reciprocal_rank_fusion",
    "normalize_vector_results",
    "normalize_graph_results",
    "rerank_results",
    "apply_topic_relevance_boost",
]
