"""Embedding utilities for HiGraph-CPG using Neo4j GenAI plugin.

All embeddings are generated server-side via Neo4j's genai.vector.encodeBatch()
procedure, which calls OpenAI's API directly. This avoids needing the OpenAI Python
SDK as a project dependency for embedding operations.

Requires:
    - Neo4j with GenAI plugin installed
    - OpenAI API key passed via api_key parameter

Default model: text-embedding-3-small (1536 dimensions)

Procedure signature:
    genai.vector.encodeBatch(
        resources :: LIST<STRING>,
        provider :: STRING,            -- 'OpenAI'
        configuration :: MAP           -- {token: $key, model: 'text-embedding-3-small'}
    ) YIELD index, resource, vector
"""

DEFAULT_MODEL = "text-embedding-3-small"
DEFAULT_PROVIDER = "OpenAI"
DEFAULT_DIMENSIONS = 1536


def _build_config(api_key: str, model: str = DEFAULT_MODEL) -> dict:
    """Build the configuration map for genai.vector.encodeBatch."""
    return {"token": api_key, "model": model}


def embed_node_property(
    tx,
    label: str,
    id_property: str,
    id_value: str,
    text_property: str,
    embedding_property: str = "embedding",
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
):
    """Generate and store an embedding for a single node's text property.

    Args:
        tx: Neo4j transaction or session
        label: Node label (e.g., "Recommendation")
        id_property: Property name used as identifier (e.g., "rec_id")
        id_value: Value of the identifier
        text_property: Property containing text to embed (e.g., "rec_text")
        embedding_property: Property to store the embedding vector
        model: OpenAI embedding model name
        api_key: OpenAI API key
    """
    query = f"""
    MATCH (n:{label} {{{id_property}: $id_value}})
    WITH n, [n.{text_property}] AS texts
    CALL genai.vector.encodeBatch(texts, $provider, $config) YIELD vector
    CALL db.create.setNodeVectorProperty(n, '{embedding_property}', vector)
    RETURN n.{id_property} AS id, size(vector) AS dimensions
    """
    result = tx.run(
        query,
        id_value=id_value,
        provider=DEFAULT_PROVIDER,
        config=_build_config(api_key, model),
    )
    return result.single()


def batch_embed_nodes(
    tx,
    label: str,
    text_property: str,
    embedding_property: str = "embedding",
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
    limit: int | None = None,
):
    """Generate and store embeddings for all nodes of a given label that lack embeddings.

    Args:
        tx: Neo4j transaction or session
        label: Node label to process
        text_property: Property containing text to embed
        embedding_property: Property to store the embedding vector
        model: OpenAI embedding model name
        api_key: OpenAI API key
        limit: Max number of nodes to process (None = all)
    """
    limit_clause = f"LIMIT {limit}" if limit else ""

    query = f"""
    MATCH (n:{label})
    WHERE n.{embedding_property} IS NULL AND n.{text_property} IS NOT NULL
    WITH collect(n) AS nodes, collect(n.{text_property}) AS texts
    {limit_clause}
    CALL genai.vector.encodeBatch(texts, $provider, $config) YIELD index, vector
    WITH nodes[index] AS node, vector
    CALL db.create.setNodeVectorProperty(node, '{embedding_property}', vector)
    RETURN count(*) AS embedded_count
    """
    result = tx.run(
        query,
        provider=DEFAULT_PROVIDER,
        config=_build_config(api_key, model),
    )
    return result.single()


def similarity_search(
    tx,
    index_name: str,
    query_text: str,
    top_k: int = 5,
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
):
    """Perform a vector similarity search using a text query.

    Generates an embedding for the query text, then searches the vector index.

    Args:
        tx: Neo4j transaction or session
        index_name: Name of the vector index (e.g., "recommendation_embedding")
        query_text: Natural language query
        top_k: Number of results to return
        model: OpenAI embedding model name
        api_key: OpenAI API key

    Returns:
        List of (node, score) tuples
    """
    query = f"""
    CALL genai.vector.encodeBatch([$query_text], $provider, $config) YIELD vector AS queryEmbedding
    CALL db.index.vector.queryNodes('{index_name}', $top_k, queryEmbedding)
    YIELD node, score
    RETURN node, score
    ORDER BY score DESC
    """
    result = tx.run(
        query,
        query_text=query_text,
        top_k=top_k,
        provider=DEFAULT_PROVIDER,
        config=_build_config(api_key, model),
    )
    return [(record["node"], record["score"]) for record in result]


def pairwise_cosine_similarity(tx, label: str, id1: str, id2: str, id_property: str, embedding_property: str = "embedding"):
    """Compute exact cosine similarity between two nodes using native Cypher function.

    Args:
        tx: Neo4j transaction or session
        label: Node label
        id1: First node's identifier value
        id2: Second node's identifier value
        id_property: Property name used as identifier
        embedding_property: Property storing the embedding vector

    Returns:
        Cosine similarity score (float)
    """
    query = f"""
    MATCH (a:{label} {{{id_property}: $id1}})
    MATCH (b:{label} {{{id_property}: $id2}})
    RETURN vector.similarity.cosine(a.{embedding_property}, b.{embedding_property}) AS similarity
    """
    result = tx.run(query, id1=id1, id2=id2)
    record = result.single()
    return record["similarity"] if record else None
