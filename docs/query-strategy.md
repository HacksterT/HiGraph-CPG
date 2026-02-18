# Query Strategy: Hybrid Search & Re-ranking for HiGraph-CPG

## Overview

This document defines the retrieval architecture for querying the HiGraph-CPG knowledge graph. The system combines vector similarity search (semantic) with graph traversal (structural) to produce clinically relevant results, then applies re-ranking before answer generation.

**Status**: Implemented (Phase 3: Query API & Phase 4: Chatbot logic)
**Dependencies**: Phase 1 (schema + vector indexes), Phase 2 (populated graph with real CPG data)

---

## The Problem

Neither vector search nor graph traversal alone is sufficient for clinical queries:

- **Vector search** finds semantically similar text but misses structural relationships. "Metformin" and "kidney disease" are not close in embedding space, but they are 2 hops apart in the graph via a Contraindication node.
- **Graph traversal** finds structurally connected entities but requires knowing the right starting node and traversal pattern. A clinician asking a natural language question doesn't think in Cypher.

The solution is a **hybrid retrieval pipeline** that uses both, followed by re-ranking to surface the most clinically relevant results.

---

## Architecture

┌──────────────────────────────────────────────────────────────┐
│                        User Query                             │
│  "What should I prescribe for a diabetic patient with CKD?"  │
└────────────────────────┬─────────────────────────────────────┘
                         │
                ┌────────▼─────────┐
                │   Query Router    │
                │ (Claude Haiku 4)  │
                │                   │
                │  1. Analyzes NL   │
                │  2. Extracts info │
                │  3. Selects Path  │
                └──────┬───┬───────┘
                       │   │
          ┌────────────▼┐  ┌▼───────────────┐
          │ Vector Path │  │  Graph Path    │
          │ (ANN Search)│  │ (Traversals)   │
          │   Always    │  │ If Graph/Hybrid│
          └────────────┬┘  └┬───────────────┘
                       │    │
                ┌──────▼────▼──────┐
                │  Result Fusion   │
                │      (RRF)       │
                └────────┬─────────┘
                         │
                ┌────────▼─────────┐
                │    Reranker      │
                │ (Clinical Rules) │
                └────────┬─────────┘
                         │
                ┌────────▼─────────┐
                │ Answer Generator │
                │ (Claude Sonnet 4)│
                └──────────────────┘

---

## Pipeline Stages

### Stage 1: Analysis & Routing (`QueryRouter`)

Before retrieval, the **Query Router** analyzes the user's question to extract structured metadata and determine the retrieval strategy (Vector, Graph, or Hybrid).

**Active Approach**:
The `QueryRouter` (implemented in `api/services/query_router.py`) performs a **single-pass extraction and routing** call using **Claude Haiku 4**. This combines intent classification, entity extraction, and retrieval strategy selection into one high-efficiency API request.

**Extracted Metadata**:

- **Intent**: (Treatment recommendation, evidence lookup, safety check, etc.)
- **Entities**: (Conditions, Medications, Topics, Rec IDs)
- **Routing Decision**:
  - `VECTOR`: Conceptual/broad questions.
  - `GRAPH`: Specific lookups on a single entity.
  - `HYBRID`: Complex scenarios with 2+ factors (default for answer generation).

---

### Stage 2a: Vector Retrieval Path

**Purpose**: Find semantically relevant nodes regardless of how they're connected in the graph.

**How it works**:

1. Embed the query text using the Neo4j GenAI plugin (server-side)
2. Search the vector indexes via `db.index.vector.queryNodes()` which performs an **ANN (Approximate Nearest Neighbor)** search using **Cosine Similarity**.
3. Return top-K candidates with similarity scores

**Which indexes to search** (depends on intent):

| Intent | Primary Index | Secondary Index |
|--------|--------------|-----------------|
| Treatment recommendation | `recommendation_embedding` | `intervention_embedding` |
| Drug information | `intervention_embedding` | `recommendation_embedding` |
| Clinical scenario | `scenario_embedding` | `recommendation_embedding` |
| General / unclear | All three indexes | — |

**Cypher pattern**:

```cypher
CALL genai.vector.encodeBatch([$queryText], 'OpenAI', {
    token: $apiKey, model: 'text-embedding-3-small'
}) YIELD vector AS queryEmbedding
CALL db.index.vector.queryNodes('recommendation_embedding', $topK, queryEmbedding)
YIELD node, score
RETURN node, score, labels(node)[0] AS nodeType
ORDER BY score DESC
```

**Top-K sizing**: Retrieve 20 candidates (generous) to give the re-ranker enough to work with.

---

### Stage 2b: Graph Retrieval Path

**Purpose**: Find structurally relevant nodes using the extracted entities and the graph's relationship structure.

**How it works**:

1. Map extracted entities to graph nodes (fuzzy match on names/IDs)
2. Select a Cypher traversal template based on intent
3. Execute the traversal to collect connected context

**Traversal templates by intent**:

#### Treatment recommendation

```cypher
// Find recommendations for a condition, filtered by patient characteristics
MATCH (cs:ClinicalScenario)-[t:TRIGGERS]->(r:Recommendation)
WHERE r.status = 'Active'
  AND (cs.name CONTAINS $condition OR cs.description CONTAINS $condition)
WITH r, t
OPTIONAL MATCH (r)-[:RECOMMENDS]->(i:Intervention)
OPTIONAL MATCH (pc:PatientCharacteristic)-[m:MODIFIES]->(r)
WHERE pc.characteristic_id IN $patientChars
OPTIONAL MATCH (ci:Contraindication)-[:CONTRAINDICATES]->(i)
OPTIONAL MATCH (ci)-[:APPLIES_TO]->(pc2:PatientCharacteristic)
WHERE pc2.characteristic_id IN $patientChars
RETURN r, i, pc, m, ci, t.priority AS priority
ORDER BY t.priority
```

#### Drug safety check

```cypher
// Given an intervention, find contraindications relevant to patient
MATCH (i:Intervention)
WHERE toLower(i.name) CONTAINS toLower($drugName)
OPTIONAL MATCH (i)-[:CAUSES]->(ae:AdverseEvent)
OPTIONAL MATCH (ci:Contraindication)-[:CONTRAINDICATES]->(i)
OPTIONAL MATCH (ci)-[:APPLIES_TO]->(pc:PatientCharacteristic)
WHERE pc.characteristic_id IN $patientChars
RETURN i, ae, ci, pc
```

#### Evidence lookup

```cypher
// Trace recommendation back through evidence to studies
MATCH (r:Recommendation {rec_id: $recId})
-[:BASED_ON]->(eb:EvidenceBody)
-[:INCLUDES]->(s:Study)
RETURN r, eb, s
```

**Entity resolution**: Map extracted terms to graph nodes using a combination of:

- Exact match on known IDs
- Fuzzy text match on `name` / `description` properties (using `toLower() CONTAINS`)
- Vector similarity as fallback for ambiguous terms

---

### Stage 3: Result Fusion

Merge results from both retrieval paths into a single ranked list using **Reciprocal Rank Fusion (RRF)**.

**Implementation**:
The system uses the RRF algorithm implemented in `api/services/fusion.py`.

```
RRF_score(node) = Σ  1 / (k + rank_in_path)
                  for each path where node appears
```

Where `k` is a constant (set to 60). Nodes appearing in both paths (e.g., found via semantic search AND specifically linked in the graph) receive a significant ranking boost.

**Deduplication**: Results are automatically deduplicated by `rec_id`, keeping the highest aggregated RRF score.

---

### Stage 4: Re-ranking (`reranker.py`)

Re-score the fused candidates using **Clinical Rule-based Boosting**. This ensures the most actionable and scientifically rigorous recommendations surface to the top of the context window.

**Multipliers Applied**:
The system applies property-based multipliers to the base (RRF or cosine) score:

- **Recommendation Strength**:
  - `Strong` → 1.2x boost
  - `Weak` → 1.0x (neutral)
  - `Neither` → 0.9x penalty
- **Evidence Quality**:
  - `High` → 1.15x boost
  - `Moderate` → 1.05x boost
  - `Low` → 0.95x penalty
  - `Very Low` → 0.85x penalty
- **Direction**:
  - `For` → 1.05x boost (actionable)
  - `Against` / `Neither` → 1.0x
- **Topic Relevance**:
  - If a returned recommendation matches a topic extracted by the `QueryRouter`, it receives an additional **1.1x relevance boost**.

This approach is fast, deterministic, and ensures clinical safety and evidence rigor are prioritized over raw semantic similarity.

---

### Stage 5: Answer Generation

Feed the top re-ranked results to an LLM to generate a natural language answer.

**Context assembly**: For each top result node, traverse 1-2 hops to gather supporting context:

```
Recommendation node → expand to:
  - Evidence quality (via BASED_ON → EvidenceBody.quality_rating)
  - Key studies (via BASED_ON → EvidenceBody → INCLUDES → Study)
  - Contraindications (via RECOMMENDS → Intervention → CONTRAINDICATED_BY)
  - Patient modifiers (via PatientCharacteristic → MODIFIES)
```

**Prompt structure**:

```
You are a clinical decision support assistant for VA/DoD clinicians.
Answer the following question using ONLY the provided evidence.
Cite recommendation IDs and study PMIDs when referencing evidence.
Flag any contraindications or safety concerns prominently.

Question: {user_query}

Evidence:
{assembled context from top-K results with citations}
```

**Citation tracking**: Every fact in the answer should trace back to a specific node in the graph. This is a key advantage of the knowledge graph over plain RAG — full provenance.

---

## Retrieval Strategy Selection

Not every query needs all paths. Use the query analyzer output to select the appropriate strategy:

| Query Type | Vector Path | Graph Path | Example |
|------------|:-----------:|:----------:|---------|
| Open-ended / exploratory | Yes | Light | "Tell me about diabetes medications" |
| Specific recommendation | Light | Yes | "What does the CPG say about metformin?" |
| Patient-specific | Yes | Yes (with patient char filter) | "What should I prescribe for a diabetic with CKD?" |
| Safety check | No | Yes (contraindication traversal) | "Can I give metformin to a patient with eGFR 25?" |
| Evidence lookup | No | Yes (evidence chain traversal) | "What studies support the GLP-1 RA recommendation?" |
| Comparison | Yes | Yes (parallel traversals) | "Compare SGLT2 inhibitors vs GLP-1 RAs for CV benefit" |

---

## Performance Targets

| Stage | Target Latency | Notes |
|-------|---------------|-------|
| Query analysis | <500ms | LLM call or local rules |
| Vector retrieval | <100ms | Native vector index ANN |
| Graph traversal | <200ms | Indexed Cypher queries |
| Result fusion | <10ms | In-memory scoring |
| Re-ranking (rules) | <10ms | Property-based multipliers |
| Re-ranking (LLM) | <2s | Single LLM call with 20 candidates |
| Answer generation | <3s | LLM call with assembled context |
| **Total (rules)** | **<1s** | Without LLM re-ranking |
| **Total (LLM rerank)** | **<6s** | With LLM re-ranking + answer gen |

---

### Build Status (February 2026)

- [x] **Query Router**: Functional (Claude Haiku 4)
- [x] **Hybrid Path**: Vector + Cypher Templates
- [x] **Fusion**: Reciprocal Rank Fusion implementation
- [x] **Reranking**: Rule-based clinical weighting
- [x] **Generation**: Claude Sonnet 4 with citation tracking

---

## Relationship to Existing Infrastructure

Everything described here builds on Phase 1 infrastructure already in place:

| Component | Phase 1 Foundation | Query Strategy Addition |
|-----------|-------------------|------------------------|
| Vector indexes | `recommendation_embedding`, `scenario_embedding`, `intervention_embedding` created | ANN search via `db.index.vector.queryNodes()` |
| Embeddings | `genai.vector.encodeBatch()` utility in `utils/embeddings.py` | Query-time embedding for search |
| Graph schema | 17 node types, all relationships defined | Cypher traversal templates per intent |
| Traversal patterns | 7 tested patterns in `scripts/example_traversals.cypher` | Parameterized versions as retrieval templates |
| Cosine similarity | `vector.similarity.cosine()` verified | Pairwise scoring in fusion/rerank |

---

**Document Version**: 1.0
**Created**: February 4, 2026
**Status**: Design — pending Phase 2 completion before implementation
