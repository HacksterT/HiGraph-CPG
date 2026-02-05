# Extraction Strategy: CPG-to-Knowledge-Graph Pipeline

## Why a Knowledge Graph Instead of Traditional RAG

### The Problem with Document Chunking

The typical RAG (Retrieval-Augmented Generation) approach to clinical documents follows this pattern:

1. Parse PDF into text
2. Chunk text into 500-1000 token segments
3. Embed each chunk as a vector
4. At query time, retrieve top-K similar chunks and feed to an LLM

This works for unstructured documents. Clinical practice guidelines are not unstructured. They are highly structured documents following the GRADE methodology, with explicit relationships between recommendations, evidence bodies, studies, key questions, and patient populations. Chunking destroys this structure:

- A text chunk containing a recommendation loses its connection to the studies that support it
- A chunk containing a contraindication loses its connection to the intervention it contraindicates
- Semantic similarity between "metformin" and "kidney disease" is low in embedding space, but in the CPG graph they are 2 hops apart via a Contraindication node

The HiGraph-CPG approach inverts this: instead of chunking a document and hoping retrieval finds the right pieces, we **extract the document's inherent structure** into a typed graph where relationships are explicit and traversable.

### What the Graph Buys Us

Each node in the graph is a semantically meaningful entity — not an arbitrary text fragment. A Recommendation node knows:
- Its evidence strength and direction (Strong For, Weak Against, etc.)
- Which EvidenceBody supports it (via BASED_ON relationship)
- Which studies underlie that evidence (via INCLUDES relationship)
- Which KeyQuestion it answers (via LEADS_TO relationship)
- Its topic and category within the guideline

This means a query like "What should I prescribe for a diabetic patient with CKD?" can be answered by:
1. **Vector search** on recommendation text to find semantically relevant nodes
2. **Graph traversal** to check contraindications, find supporting evidence, and filter by patient characteristics
3. **Combining both** via the hybrid retrieval strategy documented in `tasks/query-strategy.md`

---

## Pipeline Architecture

### Data Flow

```
┌──────────────────────────┐
│  Source PDF               │
│  (VA/DoD CPG, 165 pages) │
└───────────┬──────────────┘
            │
    ┌───────▼───────────────────────┐
    │  Stage 1: PDF Preprocessing    │
    │                                │
    │  PyMuPDF: extract TOC,         │
    │           split sections       │
    │  pdfplumber: extract tables    │
    │  marker-pdf: convert to        │
    │              markdown          │
    │                                │
    │  Output: document_map.json,    │
    │          tables/*.json,        │
    │          sections/*.md         │
    └───────────┬───────────────────┘
                │
    ┌───────────▼───────────────────┐
    │  Stage 2: LLM Entity           │
    │           Extraction           │
    │                                │
    │  Claude 3.5 Sonnet processes   │
    │  each entity type using        │
    │  purpose-built prompt          │
    │  templates with JSON schemas   │
    │                                │
    │  Batch processing with         │
    │  checkpoint/resume             │
    │                                │
    │  Output: recommendations.json, │
    │          key_questions.json,    │
    │          studies.json,          │
    │          evidence_bodies.json   │
    └───────────┬───────────────────┘
                │
    ┌───────────▼───────────────────┐
    │  Stage 3: PubMed Enrichment    │
    │                                │
    │  Bio.Entrez resolves PMIDs     │
    │  from parsed citations         │
    │  Fetches abstracts, MeSH       │
    │  terms, full metadata          │
    │                                │
    │  Cached cross-guideline to     │
    │  avoid duplicate API calls     │
    │                                │
    │  Output: enriched studies.json │
    └───────────┬───────────────────┘
                │
    ┌───────────▼───────────────────┐
    │  Stage 4: Relationship         │
    │           Inference            │
    │                                │
    │  Topic matching + text         │
    │  similarity + document         │
    │  structure analysis            │
    │                                │
    │  Confidence scoring:           │
    │  >0.8 auto-accept             │
    │  0.5-0.8 flagged              │
    │  <0.5 manual review           │
    │                                │
    │  Output: relationships.json    │
    └───────────┬───────────────────┘
                │
    ┌───────────▼───────────────────┐
    │  Stage 5: Graph Population     │
    │                                │
    │  Neo4j MERGE creates nodes     │
    │  and relationships             │
    │  Idempotent (safe to re-run)   │
    │                                │
    │  Output: populated Neo4j       │
    └───────────┬───────────────────┘
                │
    ┌───────────▼───────────────────┐
    │  Stage 6: Embedding            │
    │           Generation           │
    │                                │
    │  Neo4j GenAI plugin calls      │
    │  OpenAI text-embedding-3-small │
    │  on node text properties       │
    │  (rec_text, question_text,     │
    │   key_findings)                │
    │                                │
    │  Stored as node properties     │
    │  via db.create.setNodeVector   │
    │  Property()                    │
    │                                │
    │  Output: vector-indexed nodes  │
    └───────────────────────────────┘
```

### Why Embeddings Come Last

Embeddings are generated **after** graph population, not during PDF processing. This is deliberate:

1. **We embed structured data, not raw text.** The text being embedded (`rec_text`, `question_text`, `key_findings`) has been extracted, validated, and cleaned by the LLM extraction stage. It's higher quality than raw PDF text.

2. **The graph structure handles what embeddings cannot.** Embeddings capture semantic similarity. The graph captures structural relationships (evidence chains, contraindications, patient modifiers). Together they form the hybrid retrieval architecture described in `tasks/query-strategy.md`.

3. **Embedding generation requires an external API** (OpenAI via the Neo4j GenAI plugin). It may fail independently of the extraction pipeline. Keeping it as a separate stage means you can populate the graph and verify it before generating embeddings.

4. **Embeddings are regenerable.** If you switch embedding models (e.g., from `text-embedding-3-small` to a future model), you can re-run `generate_embeddings.py` without re-extracting or re-populating.

---

## Configuration-Driven Design

### The Reusability Problem

VA/DoD publishes CPGs for dozens of conditions: diabetes, hypertension, CKD, heart failure, COPD, chronic pain, etc. These guidelines share a common structure (GRADE methodology, recommendations tables, key questions, evidence appendices, references) but differ in specifics:

- Different page ranges for each section
- Different table column headers (footnote markers like "Strengtha" vs "Strength")
- Different numbers of recommendations, key questions, and studies
- Different topic/subtopic categories

### The Solution: YAML Configuration

Each guideline gets a configuration file that parameterizes all guideline-specific values. The pipeline code reads this config and adapts accordingly.

```yaml
# configs/guidelines/diabetes-t2-2023.yaml
guideline:
  id: "CPG_DM_2023"
  slug: "diabetes-t2-2023"
  disease_condition: "Type 2 Diabetes Mellitus"
  version: "6.0"
  publication_date: "2023-05-01"
  organization: "VA/DoD"
  full_title: "VA/DoD Clinical Practice Guideline for the Management of Type 2 Diabetes Mellitus"

source:
  pdf_filename: "VADOD-Diabetes-CPG_Final_508.pdf"
  total_pages: 165

sections:
  recommendations_table:
    start_page: 25
    end_page: 70
    column_mapping:
      "Topic": "topic"
      "Subtopic": "subtopic"
      "#": "rec_number"
      "Recommendation": "rec_text"
      "Strengtha": "strength_raw"
      "Categoryb": "category"
  key_questions_picots:
    start_page: 78
    end_page: 87
  key_questions_table:
    start_page: 90
    end_page: 91
  evidence_tables:
    start_page: 109
    end_page: 113
  references:
    start_page: 150
    end_page: 165

expected_counts:
  recommendations: 54
  key_questions: 12
  studies: 103
  evidence_bodies: 12

extraction:
  llm_provider: "claude"
  batch_size: 5
```

### What This Enables

To add the Hypertension CPG, the only work required is:
1. Open the PDF and identify section page ranges
2. Write a new `configs/guidelines/hypertension-2020.yaml`
3. Run `python scripts/pipeline/run_pipeline.py --config configs/guidelines/hypertension-2020.yaml`
4. Manual validation at checkpoints

No code changes. The same extraction templates, PubMed integration, relationship inference, and graph population logic handles any VA/DoD CPG.

---

## Entity Extraction Approach

### How LLM Extraction Works

Each entity type has a **template module** that defines three things:

1. **A prompt template** — Instructions for the LLM, formatted with the actual data to extract from. Includes the expected output JSON schema, extraction rules, and examples.

2. **A JSON schema** — Machine-readable definition of the expected output structure. Used for automated validation.

3. **A validation function** — Checks extracted data against business rules (enum values, required fields, text length minimums).

The extraction flow for each entity type:

```
Raw data (tables, markdown)
    -> Prompt template formats data into LLM prompt
    -> ai_client sends to Claude/GPT-4 with retry logic
    -> LLM returns structured JSON
    -> batch_processor saves checkpoint
    -> Validation checks against schema + business rules
    -> Validated JSON saved to extracted/ directory
```

### Entity Types and Their Sources

| Entity | Source Location | Extraction Method | Count (Diabetes) |
|--------|---------------|-------------------|-----------------|
| Recommendation | Table 5 (pp25-70) | LLM extracts from table rows | 54 |
| KeyQuestion | Appendix A (pp78-87) + Table A-2 (pp90-91) | LLM extracts PICOTS from narrative + table | 12 |
| EvidenceBody | Appendix A (pp78-87) | LLM extracts synthesis + GRADE rating | 12 |
| Study | References (pp150-165) | LLM parses citations + PubMed resolves metadata | 103 |
| Guideline | Configuration file | Direct from config (no LLM) | 1 |
| ClinicalModule | Configuration file + TOC | Direct from config (no LLM) | Varies |

### Batch Processing and Checkpointing

Extraction uses `batch_processor.py` to process entities in batches of 5-10 items. After each batch:
- Results are saved to a checkpoint file in `data/guidelines/{slug}/checkpoints/`
- If the process is interrupted (API failure, rate limit, crash), it resumes from the last checkpoint
- A progress report tracks completion percentage and any errors

This is important because LLM extraction costs money (API calls) and can be slow. You don't want to re-extract 50 recommendations because batch 51 failed.

### Validation Gates

Each entity type has a manual validation checkpoint:

| Checkpoint | Review | Threshold | Rationale |
|-----------|--------|-----------|-----------|
| Recommendations | 10 random samples | >95% accuracy | Largest set, most critical clinical content |
| Key Questions | All 12 reviewed | 100% accuracy | Small set, PICOTS must be complete |
| Studies | PMID resolution rate | >90% resolved | PubMed is authoritative source |
| Relationships | Low-confidence links | <10 flagged | Evidence chains must be reliable |

If a checkpoint fails, prompts are adjusted and the failed batches are re-extracted. The checkpoint/resume system makes this efficient.

---

## Resilience and Fallback Strategy

The pipeline is designed to fail gracefully at every stage, with multiple recovery options.

### PDF Parsing Fallbacks

The primary table extraction tool is **pdfplumber**, which works well with digitally-created PDFs (not scanned images). If pdfplumber produces poor results for specific tables:

1. **Docling + Tesseract OCR** — A proven fallback for tables where layout-based parsing fails. Tesseract reads the rendered pixels rather than interpreting PDF layout instructions, which handles image-based tables, unusual formatting, and complex merged cells more reliably. This approach has been validated separately with good results on clinical tables.

2. **Manual column mapping adjustments** — The YAML config has `column_mapping` and `alt_column_names` fields. If table headers vary across pages (e.g., "Strengtha" on page 25 but "Strength" on page 40), the config handles both without code changes.

The pipeline is modular: `extract_tables.py` just needs to produce JSON with normalized column names. The parsing tool underneath can be swapped without touching any downstream stages.

For PDF-to-markdown conversion, **marker-pdf** is the primary tool with **PyMuPDF** as an automatic fallback (marker-pdf requires Python <=3.13). Both produce usable markdown for the LLM extraction stage.

### LLM Extraction Resilience

- **Automatic retry with exponential backoff** — `ai_client.py` retries failed API calls (rate limits, timeouts, transient errors) with configurable delay.
- **JSON parsing with error recovery** — If the LLM returns malformed JSON, the client attempts to extract valid JSON from the response before failing.
- **Batch checkpointing** — After every batch of 5-10 items, results are saved to `checkpoints/`. A crash at batch 8 of 11 loses nothing — the pipeline resumes from batch 8.
- **Schema validation per entity** — Every extracted item is validated against its JSON schema and business rules (valid enum values, required fields, minimum text lengths). Invalid items are flagged, not silently accepted.
- **LLM provider fallback** — `ai_client.py` supports both Claude and GPT-4. If one provider has an outage, the config can be switched to the other without changing any extraction code.

### PubMed Resilience

- **Rate limiting** — Respects PubMed's rate limits (10 req/sec with API key, 3/sec without). Automatic throttling prevents bans.
- **Cross-guideline caching** — Resolved PMIDs are cached at `data/shared/pubmed_cache/`. A study cited by both the diabetes and hypertension CPGs is only fetched once.
- **Graceful degradation** — If PubMed is unreachable or a citation can't be resolved, the Study node is created with whatever citation data was parsed from the PDF. Unresolved studies are flagged in `manual_review/` for later resolution.

### Relationship Inference Resilience

- **Confidence scoring with thresholds** — Every inferred relationship gets a confidence score (0-1). Only high-confidence links (>0.8) are auto-accepted. Medium-confidence (0.5-0.8) are flagged for review. Low-confidence (<0.5) are excluded. Thresholds are configurable in the YAML config.
- **Multiple inference strategies** — Relationship linking uses topic matching, text similarity (TF-IDF), and explicit mention detection. The combined score is more robust than any single strategy.

### Graph Population Resilience

- **MERGE idempotency** — All Cypher operations use `MERGE`, not `CREATE`. Re-running any population script updates existing nodes rather than creating duplicates. The entire pipeline is safe to re-run.
- **Deterministic IDs** — Entity IDs follow the pattern `{GUIDELINE_ID}_{PREFIX}_{NUMBER}` (e.g., `CPG_DM_2023_REC_001`). Running the pipeline twice produces the same IDs, ensuring consistency.

### Overall Recovery

If any stage fails, the orchestrator (`run_pipeline.py`) reports which stage failed and prints the exact `--start-from` command to resume. No previous stages need to be re-run. Combined with batch checkpointing within stages, the worst-case data loss from any failure is a single batch of 5-10 items.

---

## Relationship Inference

### The Challenge

The CPG document doesn't explicitly state "Recommendation 8 is based on Evidence Body 3 which synthesizes Studies 45, 67, and 89." These relationships are implicit in the document structure. The pipeline must infer them.

### Strategies

**Recommendation -> KeyQuestion (LEADS_TO)**:
1. **Topic matching**: Recommendations in the "Pharmacotherapy" topic area likely relate to KQ 5 about pharmacotherapy
2. **Text similarity**: Embed recommendation text and KQ text, compute cosine similarity
3. **Document structure**: Table 5 groups recommendations by topic, and KQs map to topics

**EvidenceBody -> KeyQuestion (ANSWERS)**:
1. **Direct mapping**: Each KQ section in Appendix A contains exactly one evidence synthesis -- this is a 1:1 structural relationship

**EvidenceBody -> Study (INCLUDES)**:
1. **Reference number matching**: Evidence sections cite studies by reference number (e.g., "[45, 67, 89]")
2. **LLM-assisted**: Ask the LLM to identify which reference numbers appear in each evidence synthesis paragraph

### Confidence Scoring

Each inferred relationship gets a confidence score (0-1):
- **>0.8**: Auto-accepted into the graph
- **0.5-0.8**: Included but flagged for review in `manual_review/low_confidence_links.json`
- **<0.5**: Excluded, sent to manual review

The threshold is configurable in the guideline YAML.

---

## Graph Population

### ID Generation

Entity IDs are deterministic and guideline-scoped:

```
{GUIDELINE_ID}_{ENTITY_PREFIX}_{NUMBER}

Examples:
  CPG_DM_2023_REC_001    (Recommendation 1)
  CPG_DM_2023_KQ_005     (Key Question 5)
  CPG_DM_2023_STUDY_045  (Study 45)
  CPG_DM_2023_EVB_003    (Evidence Body 3)
```

This pattern:
- **Prevents collisions** when multiple guidelines coexist in Neo4j
- **Is deterministic** -- running the pipeline twice produces the same IDs (idempotent)
- **Is traceable** -- you can tell which guideline an entity came from by its ID

### MERGE-Based Idempotency

All population scripts use Cypher `MERGE` (not `CREATE`):

```cypher
MERGE (r:Recommendation {rec_id: $rec_id})
SET r.rec_text = $rec_text,
    r.strength = $strength,
    r.direction = $direction,
    r.topic = $topic,
    ...
```

This means re-running the pipeline updates existing nodes rather than creating duplicates. Properties are overwritten with the latest extraction data.

### Embedding Generation (Separate Step)

After all nodes are populated, `generate_embeddings.py` runs as a separate stage:

1. Queries Neo4j for all nodes of a given label that lack embeddings
2. Collects their text properties (`rec_text`, `question_text`, `key_findings`)
3. Calls `genai.vector.encodeBatch()` via the Neo4j GenAI plugin
4. The plugin forwards the text to OpenAI's `text-embedding-3-small` API
5. Returns 1536-dimensional vectors stored on each node via `db.create.setNodeVectorProperty()`

This uses the same `utils/embeddings.py` utility built in Phase 1. The embeddings power the three vector indexes created in Phase 1:
- `recommendation_embedding` (1536 dims, cosine)
- `scenario_embedding` (1536 dims, cosine) -- populated in Phase 3 when ClinicalScenarios are extracted
- `intervention_embedding` (1536 dims, cosine) -- populated in Phase 3 when Interventions are extracted

---

## Relationship to Other Architecture Documents

| Document | Scope | Relationship to This Document |
|----------|-------|------------------------------|
| `docs/technical/SCHEMA.md` | Neo4j schema (17 node types, all properties, all relationship types) | This pipeline populates 6 of 17 node types defined there |
| `docs/technical/EMBEDDING_STRATEGY.md` | How embeddings are generated and stored (GenAI plugin, OpenAI, Cypher patterns) | This pipeline's Stage 6 uses the approach documented there |
| `docs/technical/GRAPH_TRAVERSALS.md` | Cypher query patterns for traversing the populated graph | These traversals verify that our population is correct |
| `tasks/query-strategy.md` | Hybrid search architecture (vector + graph retrieval, re-ranking) | Built on top of the populated graph this pipeline produces |
| `tasks/prd-higraph-cpg-foundation.md` | Phase 1 PRD (infrastructure, schema, vector search) | Phase 1 infrastructure is a prerequisite for this pipeline |
| `tasks/prd-higraph-cpg-data-ingestion.md` | Phase 2 PRD (this pipeline's user stories and acceptance criteria) | This document is the technical companion to that PRD |

---

## Phase 2 Scope vs Future Phases

### Phase 2 (This Pipeline)

Extracts the **evidence chain backbone**: Study -> EvidenceBody -> KeyQuestion -> Recommendation, plus the organizational hierarchy (Guideline -> ClinicalModule -> KeyQuestion).

This gives us a queryable graph where you can:
- Trace any recommendation back through its evidence to the original studies
- Search recommendations by semantic similarity
- Browse the guideline structure by module and topic

### Phase 3 (Future: Intervention Extraction)

Extends the graph with clinical decision entities: Intervention, Benefit, AdverseEvent, ClinicalScenario, PatientPopulation, PatientCharacteristic, Contraindication. These require deeper domain knowledge and more complex extraction from narrative text (not tables).

### Phase 4+ (Future: Query API, Chatbot)

Builds the retrieval and interaction layers on top of the populated graph. See `tasks/query-strategy.md` for the hybrid search architecture.

---

**Document Version**: 1.0
**Created**: February 4, 2026
**Status**: Pre-Implementation Reference
