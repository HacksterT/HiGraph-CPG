# Query Strategy: Hybrid Search & Re-ranking for HiGraph-CPG

## Overview

This document defines the retrieval architecture for querying the HiGraph-CPG knowledge graph. The system combines vector similarity search (semantic) with graph traversal (structural) to produce clinically relevant results, then applies re-ranking before answer generation.

**Status**: Design — to be implemented in Phase 3 (Query API) or Phase 4 (Chatbot)
**Dependencies**: Phase 1 (schema + vector indexes), Phase 2 (populated graph with real CPG data)

---

## The Problem

Neither vector search nor graph traversal alone is sufficient for clinical queries:

- **Vector search** finds semantically similar text but misses structural relationships. "Metformin" and "kidney disease" are not close in embedding space, but they are 2 hops apart in the graph via a Contraindication node.
- **Graph traversal** finds structurally connected entities but requires knowing the right starting node and traversal pattern. A clinician asking a natural language question doesn't think in Cypher.

The solution is a **hybrid retrieval pipeline** that uses both, followed by re-ranking to surface the most clinically relevant results.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        User Query                             │
│  "What should I prescribe for a diabetic patient with CKD?"  │
└────────────────────────┬─────────────────────────────────────┘
                         │
                ┌────────▼─────────┐
                │  Query Analyzer   │
                │  (LLM or rules)   │
                │                   │
                │  Extracts:        │
                │  - intent         │
                │  - entities       │
                │  - patient chars  │
                └───┬──────────┬───┘
                    │          │
         ┌──────────▼──┐   ┌──▼──────────────┐
         │ Vector Path  │   │ Graph Path       │
         │              │   │                  │
         │ Embed query  │   │ Build Cypher     │
         │ ANN search   │   │ from extracted   │
         │ Top-K nodes  │   │ entities         │
         │              │   │ Traverse rels    │
         └──────┬───────┘   └────────┬────────┘
                │                    │
         ┌──────▼────────────────────▼──────┐
         │         Result Fusion             │
         │  Deduplicate, merge scores        │
         │  Reciprocal Rank Fusion (RRF)     │
         │  or weighted combination          │
         └──────────────┬───────────────────┘
                        │
               ┌────────▼─────────┐
               │    Re-ranker      │
               │  Cross-encoder,   │
               │  LLM judge, or    │
               │  clinical rules   │
               └────────┬─────────┘
                        │
               ┌────────▼─────────┐
               │  Answer Generator │
               │  LLM (Claude)     │
               │  with top results │
               │  as context       │
               └──────────────────┘
```

---

## Pipeline Stages

### Stage 1: Query Analysis

Before any retrieval, analyze the user's query to extract structured information.

**Input**: Raw natural language query
**Output**: Intent classification, extracted entities, patient characteristics

**Approach options** (in order of preference):
1. **LLM-based extraction** — Send the query to Claude with a structured prompt asking it to extract entities, intent, and patient characteristics. Most flexible, handles ambiguous queries.
2. **NER + rules** — Use a clinical NER model to tag entities (drugs, conditions, lab values), then classify intent with rules. Faster, no LLM cost, but brittle.
3. **Hybrid** — Use rules for common patterns, fall back to LLM for ambiguous queries.

**Example**:
```
Query: "What should I prescribe for a diabetic patient with CKD?"

Extracted:
  intent: treatment_recommendation
  condition: Type 2 Diabetes Mellitus
  patient_characteristics: [CKD / renal impairment]
  action: prescribe (pharmacologic intervention)
```

This extraction determines which retrieval paths to activate and what Cypher patterns to use.

---

### Stage 2a: Vector Retrieval Path

**Purpose**: Find semantically relevant nodes regardless of how they're connected in the graph.

**How it works**:
1. Embed the query text using `genai.vector.encodeBatch()`
2. Search the vector indexes via `db.index.vector.queryNodes()`
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

Merge results from both retrieval paths into a single ranked list.

**Reciprocal Rank Fusion (RRF)**:
```
RRF_score(node) = Σ  1 / (k + rank_in_path)
                  for each path where node appears
```
Where `k` is a constant (typically 60). Nodes appearing in both paths get boosted.

**Alternative — Weighted combination**:
```
final_score = (vector_score * w_vector) + (graph_relevance * w_graph)
```
Where `graph_relevance` is derived from:
- Traversal distance from matched entity (closer = higher)
- Relationship type importance (CONTRAINDICATES > ALTERNATIVE_TO for safety queries)
- Node status (Active > Superseded)

**Deduplication**: Same node may appear from both paths — keep the higher score.

---

### Stage 4: Re-ranking

Re-score the fused candidates using a more precise (but slower) method.

**Option A: Cross-encoder model** (recommended for production)
- Use a model like Cohere Rerank or a fine-tuned BERT cross-encoder
- Scores each (query, candidate_text) pair directly
- More accurate than vector cosine similarity because it sees both texts together
- ~100ms for 20 candidates

**Option B: LLM-based re-ranking** (simpler, higher cost)
- Send the query + top 20 candidates to Claude in a single prompt
- Ask: "Rank these results by relevance to the query. Consider clinical safety."
- More expensive per query but requires no additional model deployment
- Can incorporate clinical reasoning (e.g., prioritize safety concerns)

**Option C: Clinical rule-based boosting** (lightweight, no extra model)
- Apply multipliers based on node properties:
  - `strength = "Strong"` → 1.2x boost
  - `status = "Active"` → required (filter out Superseded)
  - `severity = "Critical"` on Contraindication → 1.5x boost for safety queries
  - `quality_rating = "High"` on EvidenceBody → 1.1x boost
- Fast, deterministic, clinically grounded
- Can be combined with Option A or B

**Recommended approach**: Start with Option C (rule-based) for the MVP, add Option B (LLM) when the chatbot is built. Option A if query volume justifies a dedicated rerank model.

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

## Implementation Phases

This strategy does not need to be built all at once. Each piece adds value incrementally:

### MVP (Phase 3: Query API)
- Query analyzer: rule-based entity extraction
- Vector path only (single index search)
- No fusion (single path)
- Re-ranking: clinical rule-based boosting
- Return structured JSON results (no answer generation)

### Enhanced (Phase 4: Chatbot)
- Query analyzer: LLM-based extraction
- Both vector + graph paths
- RRF fusion
- Re-ranking: rule-based + LLM judge
- Answer generation with Claude + citations

### Production (Phase 5+)
- Cross-encoder re-ranking model
- Query routing optimization (skip unnecessary paths)
- Result caching for common query patterns
- Feedback loop: track which results clinicians find useful

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
