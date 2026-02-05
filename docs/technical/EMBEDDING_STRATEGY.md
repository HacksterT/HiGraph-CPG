# HiGraph-CPG Embedding Strategy

## Decision Summary

| Aspect | Choice | Rationale |
|--------|--------|-----------|
| **Embedding provider** | OpenAI `text-embedding-3-small` | Quality, 1536 dims, widely supported |
| **Embedding generation** | Neo4j GenAI plugin (`genai.vector.encodeBatch()`) | Server-side, no Python SDK needed for embeddings |
| **Vector storage** | `db.create.setNodeVectorProperty()` | Community Edition compatible |
| **Approximate search** | `db.index.vector.queryNodes()` | Native vector index, fast ANN |
| **Exact similarity** | `vector.similarity.cosine()` | Built-in Cypher function, no GDS needed |
| **Neo4j edition** | Community (via `neo4j:community` Docker tag) | Free, sufficient for project scope |

---

## How It Works — Data Flow

When you call the vector search test or any embedding operation, here is what happens step by step:

```
┌──────────────┐     Cypher query      ┌──────────────────┐    HTTPS POST     ┌─────────────┐
│  Python      │  ─────────────────►   │  Neo4j Server    │  ──────────────►  │  OpenAI API │
│  (your app)  │  (Bolt protocol,      │  (Docker)        │  (from inside     │  (cloud)    │
│              │   port 7687)          │                  │   the container)  │             │
│              │                       │  GenAI plugin    │                   │  /v1/       │
│              │                       │  receives the    │  Sends:           │  embeddings │
│              │                       │  Cypher CALL,    │  - your API key   │             │
│              │                       │  extracts text   │    (as Bearer     │  Returns:   │
│              │                       │  + config map    │     token)        │  1536-dim   │
│              │  ◄─────────────────   │                  │  ◄──────────────  │  float[]    │
│  receives    │  vector returned      │  stores vector   │  embedding        │             │
│  result      │  via Bolt             │  on the node     │  response         │             │
└──────────────┘                       └──────────────────┘                   └─────────────┘
```

### Step-by-step for a single node embedding:

1. **Python** reads your `OPENAI_API_KEY` from `.env` into a Python variable
2. **Python** sends a Cypher query over Bolt (port 7687) to Neo4j, passing the API key as a query parameter (`$config: {token: "sk-proj-...", model: "text-embedding-3-small"}`)
3. **Neo4j GenAI plugin** inside the Docker container receives the Cypher `CALL genai.vector.encodeBatch(...)`
4. **GenAI plugin** makes an HTTPS POST to `https://api.openai.com/v1/embeddings` with your API key as the `Authorization: Bearer` header and the text in the request body
5. **OpenAI** processes the text and returns a JSON response containing a 1536-element float array (the embedding vector)
6. **GenAI plugin** receives the vector and passes it back into the Cypher execution pipeline
7. **Neo4j** stores the vector on the node via `db.create.setNodeVectorProperty()`, which writes it into the vector index for fast ANN search
8. **Python** receives the confirmation (node ID + dimensions) back over Bolt

### Where your API key goes:

- Stored in `.env` on disk (git-ignored)
- Read by Python into memory at script startup
- Passed as a Cypher query parameter to Neo4j (encrypted in transit if using bolt+s, plaintext over localhost bolt)
- Neo4j GenAI plugin forwards it to OpenAI as an HTTP Bearer token
- **Not stored in Neo4j** — it is transient, used only for the duration of the procedure call
- **Not logged** by Neo4j (query parameters are not included in query logs)

### For similarity search:

The flow is the same but with an extra step — the query text gets embedded first, then the resulting vector is fed into `db.index.vector.queryNodes()` which does approximate nearest neighbor search against the pre-stored vectors in the index.

---

## Neo4j GenAI Plugin — Actual API

The GenAI plugin bundled with Neo4j 2025.12.x provides two procedures:

### `genai.vector.encodeBatch()`

The primary embedding procedure. Despite the name, it works for single texts too (just pass a 1-element list).

```
genai.vector.encodeBatch(
    resources :: LIST<STRING>,     -- texts to embed
    provider  :: STRING,           -- 'OpenAI', 'AzureOpenAI', 'Bedrock', 'VertexAI'
    configuration :: MAP           -- provider-specific config
) YIELD index, resource, vector
```

**OpenAI configuration map:**
- `token` (required) — your OpenAI API key
- `model` (optional, default: `text-embedding-ada-002`) — we override to `text-embedding-3-small`
- `dimensions` (optional) — output dimensions, defaults to model's native (1536 for text-embedding-3-small)

### `genai.vector.listEncodingProviders()`

Lists available providers and their required/optional configuration fields.

```
genai.vector.listEncodingProviders()
YIELD name, requiredConfigType, optionalConfigType, defaultConfig
```

### Note on procedure name evolution

Neo4j's embedding API has gone through several naming iterations:
1. `apoc.ml.openai.embedding()` — APOC ML (legacy)
2. `genai.vector.encode()` / `genai.vector.encodeBatch()` — GenAI plugin (current in 2025.12.x)
3. `ai.text.embed()` / `ai.text.embedBatch()` — Planned future API (not yet available as of 2025.12.1)

We use #2, which is what ships with the `neo4j:community` Docker image.

---

## Why GenAI Plugin + OpenAI

### Over APOC ML
- `genai.vector.encodeBatch()` is the officially supported path
- Better error handling and retry semantics
- Supports batch operations natively
- Provider-agnostic API (could switch to AzureOpenAI, Bedrock, or VertexAI)

### Over Local sentence-transformers
- No GPU/CPU overhead on the development machine
- Higher quality embeddings for clinical text (OpenAI models trained on diverse medical literature)
- Simpler deployment (no Python embedding service to maintain)
- Trade-off: requires API key and has per-token cost (~$0.02 per million tokens for text-embedding-3-small)

### Over GDS (Graph Data Science)
- GDS is not needed for cosine similarity. Neo4j Cypher has built-in `vector.similarity.cosine()`.
- GDS requires Enterprise Edition or a separate license for production use.
- GDS graph projections add complexity without benefit for our use case (we do node-level similarity, not graph-wide ML).

---

## Community Edition Considerations

Neo4j Community Edition has some limitations compared to Enterprise:

- **Vector property storage**: Use `db.create.setNodeVectorProperty(node, 'embedding', vector)` to store embeddings. This is the Community-compatible way (vs Enterprise's direct property assignment with `SET n.embedding = vector`).
- **Vector indexes**: `CREATE VECTOR INDEX` works identically in Community and Enterprise.
- **No GDS**: Not available in Community, but not needed (see above).
- **No property existence constraints**: `IS NOT NULL` constraints are Enterprise-only. Required properties are enforced at the application layer (Python scripts) instead.

---

## Cypher Patterns

### Generate and Store Embedding (single node)
```cypher
MATCH (r:Recommendation {rec_id: 'REC_001'})
WITH r, [r.rec_text] AS texts
CALL genai.vector.encodeBatch(texts, 'OpenAI', {
    token: $apiKey,
    model: 'text-embedding-3-small'
}) YIELD vector
CALL db.create.setNodeVectorProperty(r, 'embedding', vector)
RETURN r.rec_id, size(vector) AS dimensions
```

### Batch Embed All Nodes of a Label
```cypher
MATCH (r:Recommendation)
WHERE r.embedding IS NULL AND r.rec_text IS NOT NULL
WITH collect(r) AS nodes, collect(r.rec_text) AS texts
CALL genai.vector.encodeBatch(texts, 'OpenAI', {
    token: $apiKey,
    model: 'text-embedding-3-small'
}) YIELD index, vector
WITH nodes[index] AS node, vector
CALL db.create.setNodeVectorProperty(node, 'embedding', vector)
RETURN count(*) AS embedded_count
```

### Approximate Nearest Neighbor Search (via vector index)
```cypher
CALL genai.vector.encodeBatch([$queryText], 'OpenAI', {
    token: $apiKey,
    model: 'text-embedding-3-small'
}) YIELD vector AS queryEmbedding
CALL db.index.vector.queryNodes('recommendation_embedding', 5, queryEmbedding)
YIELD node, score
RETURN node.rec_text AS recommendation, score
ORDER BY score DESC
```

### Exact Pairwise Cosine Similarity (no GDS needed)
```cypher
MATCH (a:Recommendation {rec_id: 'REC_001'})
MATCH (b:Recommendation {rec_id: 'REC_002'})
RETURN vector.similarity.cosine(a.embedding, b.embedding) AS similarity
```

---

## Cost Estimation

Using OpenAI `text-embedding-3-small` at $0.02 per 1M tokens:

| Entity Type | Count | Avg Tokens | Total Tokens | Cost |
|-------------|-------|------------|--------------|------|
| Recommendation | 54 | ~50 | ~2,700 | <$0.01 |
| ClinicalScenario | ~20 | ~80 | ~1,600 | <$0.01 |
| Intervention | ~30 | ~40 | ~1,200 | <$0.01 |
| **Total** | ~104 | - | ~5,500 | <$0.01 |

The diabetes CPG is small enough that embedding costs are negligible.

---

## References

- [Neo4j GenAI Plugin Documentation](https://neo4j.com/docs/operations-manual/current/configuration/plugins/)
- [Neo4j Vector Index Documentation](https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/vector-indexes/)
- [OpenAI Embeddings API](https://platform.openai.com/docs/guides/embeddings)
- [db.create.setNodeVectorProperty](https://neo4j.com/docs/operations-manual/current/reference/procedures/)

---

**Document Version**: 1.1
**Last Updated**: February 4, 2026
