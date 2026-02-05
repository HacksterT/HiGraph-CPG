# API Strategy: HiGraph-CPG Query Service

## Overview

This document defines the API architecture for the HiGraph-CPG query service. The service provides semantic and structural search over the clinical practice guideline knowledge graph.

**Status**: ✅ Implemented (Phase 3 complete)
**Related**: `tasks/prd-query-api.md` (implementation PRD)

---

## Architecture Decisions

### Framework: FastAPI

**Decision**: Use FastAPI over Flask

**Rationale**:
- Native async support for concurrent Neo4j and OpenAI API calls
- Built-in OpenAPI documentation at `/docs`
- Pydantic models for request/response validation
- Type hints throughout improve maintainability
- Excellent performance for I/O-bound operations (our primary workload)

**Trade-offs**:
- Slightly more complex than Flask for simple endpoints
- Requires understanding of async/await patterns

### API Style: REST with Structured Responses

**Decision**: REST API with JSON responses (no GraphQL for MVP)

**Rationale**:
- Simpler to implement and debug
- GraphQL adds complexity without clear benefit for our use case
- Our query patterns are well-defined (vector, graph, hybrid)
- Can add GraphQL later if needed

**Endpoint Design**:
```
/api/v1/search/vector    # Semantic similarity search
/api/v1/search/graph     # Structural graph traversal
/api/v1/query            # Unified endpoint with automatic routing
```

### Authentication: None (Cloudflare Tunnel)

**Decision**: No application-level authentication

**Rationale**:
- Access controlled via Cloudflare tunnel
- Simplifies development and testing
- Authentication at tunnel level is more secure (no credentials in app)

**Future Consideration**: If API is exposed beyond tunnel, add JWT authentication.

### Graph Queries: Template-Based (Not LLM-Generated Cypher)

**Decision**: Use predefined Cypher templates with parameter substitution

**Rationale**:
- **Security**: No risk of Cypher injection
- **Predictability**: Known query patterns, easier to optimize
- **Reliability**: LLM-generated Cypher can be syntactically invalid
- **Cost**: No LLM call needed for query construction

**Trade-off**: Less flexible than dynamic Cypher generation. Mitigated by:
- Comprehensive template library (5 templates for MVP)
- Can add templates as new query patterns emerge
- LLM router can combine templates for complex queries

### Re-Ranking: Rule-Based (Not ML/LLM)

**Decision**: Use clinical rule-based re-ranking for MVP

**Rules** (implemented in `api/services/reranker.py`):
| Condition | Multiplier |
|-----------|------------|
| `strength = "Strong"` | 1.2x |
| `strength = "Weak"` | 1.0x |
| `strength = "Neither for nor against"` | 0.9x |
| `quality_rating = "High"` | 1.15x |
| `quality_rating = "Moderate"` | 1.05x |
| `quality_rating = "Low"` | 0.95x |
| `direction = "For"` | 1.05x |

**Rationale**:
- Zero additional latency
- No API costs
- Clinically grounded (Strong recommendations should rank higher)
- Deterministic and explainable

**Future Enhancement**: Add cross-encoder model or LLM judge for production.

---

## Query Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Request                           │
│                    POST /api/v1/query                            │
│                    {"question": "..."}                           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Query Router (LLM)                          │
│                                                                  │
│  Input: Natural language question                                │
│  Output: {query_type, entities, template_hint}                   │
│                                                                  │
│  Model: Claude 3.5 Haiku (fast, low cost)                        │
│  Cost: ~$0.001 per query                                         │
│  Latency: ~150-300ms                                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
           ▼                 ▼                 ▼
      VECTOR only       GRAPH only         HYBRID
           │                 │                 │
           ▼                 ▼                 ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│  Embed Query     │ │  Select Template │ │  Both Paths      │
│  (OpenAI API)    │ │  Fill Parameters │ │  Execute Parallel│
│                  │ │                  │ │                  │
│  ANN Search      │ │  Execute Cypher  │ │  Fusion (RRF)    │
│  Top-K Results   │ │  Return Nodes    │ │  Re-rank         │
└────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘
         │                    │                    │
         └────────────────────┴────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Response Assembly                           │
│                                                                  │
│  - Ranked results with scores                                    │
│  - Reasoning block (path used, timing, entities)                 │
│  - Evidence context (on demand)                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Endpoint Specifications

### GET /health

Health check endpoint.

**Response**:
```json
{
  "status": "ok",
  "neo4j": "connected",
  "version": "1.0.0"
}
```

### POST /api/v1/search/vector

Direct vector similarity search. Supports 5 node types: Recommendation, Study, KeyQuestion, EvidenceBody, ClinicalModule.

**Request**:
```json
{
  "query": "medications for diabetic kidney disease",
  "top_k": 10,
  "node_type": "Recommendation"
}
```

**Response**:
```json
{
  "results": [
    {
      "node_type": "Recommendation",
      "rec_id": "REC_019",
      "rec_text": "For adults with T2DM and established ASCVD...",
      "strength": "Strong",
      "direction": "For",
      "topic": "Pharmacotherapy",
      "similarity_score": 0.89
    }
  ],
  "reasoning": {
    "path_used": "vector",
    "embedding_time_ms": 89,
    "search_time_ms": 45,
    "total_time_ms": 134,
    "node_type_searched": "Recommendation",
    "results_count": 1
  }
}
```

### POST /api/v1/search/graph

Template-based graph traversal.

**Request**:
```json
{
  "template": "evidence_chain_full",
  "params": {
    "rec_ids": ["CPG_DM_2023_REC_019"]
  }
}
```

**Response**:
```json
{
  "results": [
    {
      "recommendation": {
        "rec_id": "CPG_DM_2023_REC_019",
        "rec_text": "...",
        "strength": "Strong"
      },
      "evidence_body": {
        "evidence_id": "CPG_DM_2023_EVB_007",
        "quality_rating": "High",
        "num_studies": 34
      },
      "key_question": {
        "kq_id": "CPG_DM_2023_KQ_007",
        "question_text": "..."
      },
      "studies": [
        {
          "title": "Empagliflozin, Cardiovascular Outcomes...",
          "pmid": "26378978",
          "journal": "N Engl J Med",
          "year": 2015
        }
      ]
    }
  ],
  "reasoning": {
    "path_used": "graph",
    "template_used": "evidence_chain_full",
    "query_time_ms": 67
  }
}
```

### POST /api/v1/query

Unified endpoint with automatic routing.

**Request**:
```json
{
  "question": "What should I prescribe for a diabetic patient with CKD?",
  "include_studies": false,
  "top_k": 10
}
```

**Response**:
```json
{
  "results": [
    {
      "rec_id": "REC_022",
      "rec_text": "For adults with type 2 diabetes mellitus and chronic kidney disease...",
      "strength": "Strong",
      "direction": "For",
      "topic": "Pharmacotherapy",
      "score": 0.92,
      "evidence_quality": "High",
      "study_count": 34,
      "source": "both"
    }
  ],
  "reasoning": {
    "routing": {
      "query_type": "HYBRID",
      "intent": "treatment_recommendation",
      "confidence": 0.95,
      "entities": {
        "conditions": ["type 2 diabetes", "CKD"],
        "medications": [],
        "patient_characteristics": [],
        "rec_ids": [],
        "topics": ["Pharmacotherapy"]
      },
      "template_hint": "recommendations_by_topic",
      "reasoning": "Patient-specific treatment question with comorbidities"
    },
    "paths_used": ["vector", "graph"],
    "template_used": "recommendations_by_topic",
    "vector_candidates": 10,
    "graph_candidates": 8,
    "fusion_method": "RRF",
    "rerank_applied": true,
    "timing": {
      "routing_ms": 245,
      "embedding_ms": 89,
      "vector_search_ms": 45,
      "graph_search_ms": 67,
      "fusion_ms": 3,
      "rerank_ms": 2,
      "total_ms": 451
    }
  }
}
```

---

## Graph Templates

### Template: `recommendation_only`

Fetch recommendations by ID list.

**Parameters**: `rec_ids` (list of strings)

**Use Case**: Retrieve specific recommendations by ID

```cypher
MATCH (r:Recommendation)
WHERE r.rec_id IN $rec_ids
RETURN r
```

### Template: `recommendation_with_evidence`

Recommendations with evidence quality context.

**Parameters**: `rec_ids` (list of strings)

**Use Case**: Show recommendations with quality ratings

```cypher
MATCH (r:Recommendation)-[:BASED_ON]->(eb:EvidenceBody)
WHERE r.rec_id IN $rec_ids
RETURN r, eb.quality_rating as quality, eb.num_studies as study_count
```

### Template: `evidence_chain_full`

Full citation chain from recommendation to studies.

**Parameters**: `rec_ids` (list of strings)

**Use Case**: Physician wants to see supporting evidence

```cypher
MATCH (r:Recommendation)-[:BASED_ON]->(eb:EvidenceBody)
      -[:ANSWERS]->(kq:KeyQuestion)
WHERE r.rec_id IN $rec_ids
OPTIONAL MATCH (eb)-[:INCLUDES]->(s:Study)
RETURN r, eb, kq, collect({
    title: s.title,
    pmid: s.pmid,
    journal: s.journal,
    year: s.year
}) as studies
```

### Template: `studies_for_recommendation`

All studies supporting a specific recommendation.

**Parameters**: `rec_id` (single string)

**Use Case**: Deep dive into evidence base

```cypher
MATCH (r:Recommendation {rec_id: $rec_id})
      -[:BASED_ON]->(eb:EvidenceBody)
      -[:INCLUDES]->(s:Study)
RETURN s.title as title, s.pmid as pmid,
       s.journal as journal, s.year as year,
       s.abstract as abstract
ORDER BY s.year DESC
```

### Template: `recommendations_by_topic`

Filter recommendations by topic.

**Parameters**: `topic` (string)

**Use Case**: Browse recommendations by category

```cypher
MATCH (r:Recommendation)
WHERE toLower(r.topic) CONTAINS toLower($topic)
   OR toLower(r.subtopic) CONTAINS toLower($topic)
RETURN r
ORDER BY r.rec_number
```

---

## Query Router Prompt

The LLM router uses this prompt to classify queries:

```
You are a query router for a clinical practice guideline knowledge graph.

Analyze the user's question and determine:
1. query_type: VECTOR | GRAPH | HYBRID
2. entities: extracted conditions, drugs, patient factors
3. intent: treatment_recommendation | evidence_lookup | drug_info | safety_check | general
4. template_hint: which graph template might be useful (if GRAPH or HYBRID)

Guidelines:
- VECTOR: Open-ended questions, semantic similarity needed
  Example: "Tell me about diabetes medications"

- GRAPH: Specific lookups, structural traversal needed
  Example: "What studies support recommendation 19?"

- HYBRID: Patient-specific questions needing both semantic match and structural context
  Example: "What should I prescribe for a diabetic with CKD?"

Available templates:
- recommendation_only: fetch recs by ID
- recommendation_with_evidence: recs + quality ratings
- evidence_chain_full: rec → evidence → studies
- studies_for_recommendation: all studies for one rec
- recommendations_by_topic: filter by topic

Respond in JSON:
{
  "query_type": "VECTOR|GRAPH|HYBRID",
  "intent": "...",
  "entities": {
    "condition": "...",
    "drug": "...",
    "comorbidity": "...",
    "rec_id": "..."
  },
  "template_hint": "...",
  "search_text": "text to embed for vector search"
}
```

---

## Result Fusion: Reciprocal Rank Fusion (RRF)

When both vector and graph paths return results, combine using RRF:

```python
def rrf_score(node, rankings, k=60):
    """
    Calculate RRF score for a node across multiple rankings.

    Args:
        node: The node ID
        rankings: Dict of {path_name: [ordered list of node IDs]}
        k: Smoothing constant (default 60)

    Returns:
        Combined RRF score
    """
    score = 0.0
    for path_name, ranked_list in rankings.items():
        if node in ranked_list:
            rank = ranked_list.index(node) + 1  # 1-indexed
            score += 1.0 / (k + rank)
    return score
```

Nodes appearing in both paths get boosted (summed scores).

---

## Re-Ranking Rules

Applied after fusion:

```python
RERANK_RULES = {
    "strength_boost": {
        "condition": lambda r: r.get("strength") == "Strong",
        "multiplier": 1.2
    },
    "quality_boost": {
        "condition": lambda r: r.get("evidence", {}).get("quality") == "High",
        "multiplier": 1.1
    },
    "active_filter": {
        "condition": lambda r: r.get("status") != "Superseded",
        "action": "filter"  # Remove if condition is False
    }
}

def apply_reranking(results):
    # Filter first
    results = [r for r in results if RERANK_RULES["active_filter"]["condition"](r)]

    # Then boost
    for result in results:
        for rule_name, rule in RERANK_RULES.items():
            if rule.get("action") == "filter":
                continue
            if rule["condition"](result):
                result["score"] *= rule["multiplier"]

    # Re-sort by score
    return sorted(results, key=lambda r: r["score"], reverse=True)
```

---

## Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Health check | <10ms | Simple DB ping |
| Query routing (LLM) | <500ms | Claude API call |
| Query embedding | <100ms | OpenAI API call |
| Vector search | <100ms | Neo4j ANN index |
| Graph traversal | <200ms | Indexed Cypher |
| Fusion + rerank | <20ms | In-memory |
| **Total (vector only)** | **<300ms** | No LLM routing |
| **Total (with routing)** | **<800ms** | Full hybrid flow |

---

## Error Handling

| Error | HTTP Status | Response |
|-------|-------------|----------|
| Invalid request body | 422 | `{"detail": [{"loc": [...], "msg": "..."}]}` |
| Unknown template | 400 | `{"detail": "Unknown template. Valid: [...]"}` |
| Missing template params | 422 | `{"detail": "Missing required param: rec_ids"}` |
| Neo4j connection failed | 503 | `{"detail": "Database unavailable"}` |
| OpenAI API error | 502 | `{"detail": "Embedding service unavailable"}` |
| Anthropic API error | 502 | `{"detail": "Routing service unavailable"}` |

---

## Future Enhancements

1. **GraphQL Endpoint**: Add if clients need flexible field selection
2. **Caching Layer**: Redis for common query patterns
3. **Cross-Encoder Re-ranking**: ML model for better ranking
4. **Query Suggestions**: Autocomplete based on graph entities
5. **Batch Queries**: Process multiple questions in one request

---

**Document Version**: 1.1
**Created**: February 5, 2026
**Updated**: February 5, 2026
**Status**: ✅ Implemented — Phase 3 complete
