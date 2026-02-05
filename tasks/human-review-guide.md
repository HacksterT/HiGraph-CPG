# Human Review Guide: Pipeline Validation Checkpoints

This guide walks you through each manual review checkpoint in the data ingestion pipeline. The pipeline is designed to stop at specific points so a human can verify quality before proceeding to the next stage. This prevents wasting LLM API credits on bad input or populating the graph with incorrect data.

**Why this matters**: LLM extraction costs real money (Anthropic API calls) and bad data in the graph is worse than no data. Each checkpoint catches a different class of error. Skipping a checkpoint means the errors compound downstream.

---

## Checkpoint A: After Preprocessing (Before Any LLM Extraction)

**Run command**:
```bash
python scripts/pipeline/run_pipeline.py --config configs/guidelines/diabetes-t2-2023.yaml --stop-after preprocess
```

**What was produced**: The preprocessing stage parsed the PDF into structured outputs. Review these before spending any API credits on LLM extraction.

**Output location**: `data/guidelines/diabetes-t2-2023/preprocessed/`

### A1: Document Map

**File**: `preprocessed/document_map.json`

Open the file and verify:
- [ ] All major sections are listed (recommendations, key questions, evidence tables, references)
- [ ] Page numbers match what you see in the actual PDF
- [ ] No sections are missing or have obviously wrong page ranges
- [ ] Section titles look correct (not garbled text from parsing errors)

**How to cross-check**: Open the PDF in any viewer and compare the table of contents (usually pages 3-5) against the document map. Page numbers should match within 1-2 pages.

### A2: Table Extraction — Recommendations (Table 5)

**File**: `preprocessed/tables/table_5_recommendations.json` (or similar)

This is the most critical table — it contains all 54 recommendations. Open the JSON and verify:

- [ ] The file contains rows (not empty or a single malformed entry)
- [ ] Row count is plausible — you should see roughly 50-60 rows (some may be header repeats across pages, which is fine; the LLM will deduplicate)
- [ ] Column names are recognizable — look for variations of: Topic, Subtopic, #, Recommendation, Strength, Category
- [ ] Spot-check 3-5 rows against the PDF:
  - Pick recommendation #1 (first in the table, around page 25)
  - Pick one from the middle (around #25, roughly page 45)
  - Pick the last recommendation (#54, around page 70)
  - For each: does the recommendation text match? Is the strength value present? Is the topic correct?

**What to look for**:
- Garbled text (especially in the Recommendation column — long text is most likely to be corrupted)
- Missing columns (if "Strength" or "Category" columns are empty for every row, the column mapping may be wrong)
- Merged rows (two recommendations collapsed into one row, or a recommendation split across two rows)
- Footnote markers appearing as column headers (e.g., "Strengtha" instead of "Strength" — this is expected and handled by the config, just verify they're present)

**If something looks wrong**: The most common fix is adjusting `column_mapping` or `alt_column_names` in `configs/guidelines/diabetes-t2-2023.yaml`. If the table structure itself is corrupted, try the Docling + Tesseract OCR fallback (see `tasks/extraction-strategy.md`, "Resilience and Fallback Strategy").

### A3: Table Extraction — Key Questions (Table A-2)

**File**: `preprocessed/tables/table_a2_key_questions.json` (or similar)

- [ ] Contains approximately 12 rows (one per key question)
- [ ] Each row has a KQ number and description
- [ ] Study counts are present (number of studies per KQ)

**Cross-check**: Open the PDF to pages 90-91 and compare against Table A-2.

### A4: Table Extraction — Evidence (Appendix E)

**File**: `preprocessed/tables/appendix_e_evidence.json` (or similar)

- [ ] Contains rows with GRADE quality ratings
- [ ] Ratings use expected values (High, Moderate, Low, Very Low)

**Cross-check**: Open the PDF to pages 109-113.

### A5: Section Markdown

**Files**: `preprocessed/sections/*.md`

Spot-check 2-3 section markdown files:
- [ ] Text is readable (not garbled)
- [ ] Headers are preserved
- [ ] The content matches the corresponding pages in the PDF
- [ ] Key questions section (pp78-87) has PICOTS structure visible

**Note**: If using PyMuPDF fallback (instead of marker-pdf), markdown quality will be basic — plain text with minimal formatting. This is acceptable as long as the text content is correct.

### Checkpoint A Decision

| Result | Action |
|--------|--------|
| All checks pass | Proceed to extraction: `--start-from extract_metadata --stop-after extract_studies` |
| Table extraction has minor issues | Adjust `column_mapping` in YAML config, re-run `--stop-after preprocess` |
| Table extraction is badly corrupted | Switch to Docling + Tesseract OCR for table extraction, re-run |
| Markdown is garbled | Check PDF quality; try alternative markdown converter |

---

## Checkpoint B1: After Recommendation Extraction

**Run command** (runs metadata + all entity extraction):
```bash
python scripts/pipeline/run_pipeline.py --config configs/guidelines/diabetes-t2-2023.yaml \
  --start-from extract_metadata --stop-after extract_recommendations
```

**Output file**: `data/guidelines/diabetes-t2-2023/extracted/recommendations.json`

### What to review

- [ ] **Count**: The file should contain exactly 54 recommendations. If significantly fewer, some batches may have failed (check `checkpoints/` for partial progress).

- [ ] **Random sample of 10**: Open the JSON and pick 10 recommendations at random. For each one, open the PDF to Table 5 and verify:
  - [ ] `rec_text` matches the PDF verbatim (not summarized, not truncated)
  - [ ] `strength` is correct ("Strong", "Weak", or "Neither for nor against")
  - [ ] `direction` is correct ("For", "Against", or "Neither")
  - [ ] `topic` matches the Topic column in the PDF
  - [ ] `category` is present and reasonable ("Reviewed, New-added", "Reviewed, Amended", etc.)

- [ ] **Strength/direction distribution**: Scan the full list. The diabetes CPG has a mix of Strong/Weak and For/Against. If every single recommendation shows "Strong" + "For", the extraction is likely defaulting rather than parsing correctly.

### Accuracy threshold

**Requirement: >95% accuracy (at least 9 of 10 sampled must be correct)**

| Result | Action |
|--------|--------|
| 9-10 of 10 correct | Proceed to key question extraction |
| 7-8 of 10 correct | Review the errors, adjust the prompt template in `scripts/extraction/templates/recommendation_template.py`, re-run `--start-from extract_recommendations --stop-after extract_recommendations` |
| <7 of 10 correct | Investigate table extraction quality (go back to Checkpoint A), then re-extract |

---

## Checkpoint B2: After Key Question Extraction

**Run command**:
```bash
python scripts/pipeline/run_pipeline.py --config configs/guidelines/diabetes-t2-2023.yaml \
  --start-from extract_key_questions --stop-after extract_key_questions
```

**Output file**: `data/guidelines/diabetes-t2-2023/extracted/key_questions.json`

### What to review

There are only 12 key questions — review all of them.

- [ ] **Count**: Exactly 12 key questions

- [ ] **For each KQ** (compare against Appendix A, pages 78-87):
  - [ ] `question_text` accurately captures the key question
  - [ ] `population` describes the target patient group
  - [ ] `intervention` describes what's being evaluated
  - [ ] `comparator` describes what it's being compared to
  - [ ] `outcomes_critical` lists outcomes rated 7-9 (critical for decision-making)
  - [ ] `outcomes_important` lists outcomes rated 4-6 (important but not critical)
  - [ ] `timing` and `setting` are present if specified in the document

- [ ] **Completeness**: No PICOTS fields should be empty unless the PDF genuinely doesn't specify them for that KQ

### Accuracy threshold

**Requirement: 100% accuracy (all 12 must be correct)**

This is a small set with high clinical importance. Every KQ must be accurate.

| Result | Action |
|--------|--------|
| All 12 correct | Proceed to evidence body extraction |
| Any errors | Fix the specific errors (may need prompt adjustment), re-run KQ extraction only |

---

## Checkpoint B3: After Evidence Body and Study Extraction

**Run command**:
```bash
python scripts/pipeline/run_pipeline.py --config configs/guidelines/diabetes-t2-2023.yaml \
  --start-from extract_evidence_bodies --stop-after extract_studies
```

Then run PubMed resolution:
```bash
python scripts/pipeline/run_pipeline.py --config configs/guidelines/diabetes-t2-2023.yaml \
  --start-from resolve_pmids --stop-after fetch_metadata
```

**Output files**:
- `data/guidelines/diabetes-t2-2023/extracted/evidence_bodies.json`
- `data/guidelines/diabetes-t2-2023/extracted/studies.json`

### Evidence bodies

- [ ] **Count**: 12 evidence bodies (one per key question)
- [ ] **GRADE ratings**: Each should have a quality_rating of High, Moderate, Low, or Very Low
- [ ] **KQ linkage**: Each evidence body should reference a kq_number matching one of the 12 KQs
- [ ] **Key findings**: The `key_findings` text should contain substantive evidence synthesis, not empty or generic text

### Studies

- [ ] **Count**: Approximately 103 studies (some variation acceptable if the reference list has non-study entries like guidelines or websites)
- [ ] **PMID resolution rate**: Check how many studies have a `pmid` field vs null. Target: >90% resolved (>93 of 103)
- [ ] **Unresolved studies**: Check `data/guidelines/diabetes-t2-2023/manual_review/` for flagged unresolved citations. These may be:
  - Grey literature (VA/DoD internal reports, websites) — expected to be unresolved
  - Misspelled author names or incorrect years — fixable by manually providing PMIDs
  - Genuinely obscure citations — mark as unresolvable

- [ ] **Spot-check 5 resolved studies**: For 5 studies that have PMIDs, verify on [PubMed](https://pubmed.ncbi.nlm.nih.gov/) that the PMID matches the correct paper (search the PMID, confirm title/authors match)

### Accuracy thresholds

| Check | Threshold | Action if failed |
|-------|-----------|------------------|
| Evidence bodies count | 12 | Re-run evidence extraction |
| GRADE ratings valid | All 12 | Fix invalid ratings manually or re-extract |
| PMID resolution | >90% | Review unresolved in manual_review/, manually resolve where possible |
| PMID accuracy (spot check) | 5/5 correct | If wrong PMIDs, check citation parsing quality |

---

## Checkpoint C: After Relationship Inference

**Run command**:
```bash
python scripts/pipeline/run_pipeline.py --config configs/guidelines/diabetes-t2-2023.yaml \
  --start-from build_relationships --stop-after build_relationships
```

**Output files**:
- `data/guidelines/diabetes-t2-2023/extracted/relationships.json`
- `data/guidelines/diabetes-t2-2023/manual_review/low_confidence_links.json` (if any)

### What to review

- [ ] **Relationship counts**: The file should contain relationships of these types:
  - LEADS_TO: Recommendation -> KeyQuestion (54 recommendations, each linked to at least one KQ)
  - ANSWERS: EvidenceBody -> KeyQuestion (12, one per KQ)
  - INCLUDES: EvidenceBody -> Study (variable, each evidence body includes multiple studies)
  - BASED_ON: Recommendation -> EvidenceBody (54, derived from LEADS_TO)
  - PART_OF: ClinicalModule -> Guideline (9 modules)
  - CONTAINS: ClinicalModule -> KeyQuestion (12 KQs distributed across modules)

- [ ] **Low-confidence links**: Open `manual_review/low_confidence_links.json`. These are relationships with confidence scores between 0.5 and 0.8.
  - For each flagged link, check if the relationship makes sense (e.g., does Recommendation 15 about "Pharmacotherapy" reasonably relate to KQ 5 about drug therapy?)
  - Accept correct links (they'll be included in the graph)
  - Reject incorrect links (remove them from the relationships file)

- [ ] **Orphan check**: Are there any recommendations not linked to any KQ? Any evidence bodies with no studies? These indicate inference failures.

- [ ] **Sample evidence chain**: Pick 2-3 recommendations and trace the full chain:
  ```
  Recommendation -> BASED_ON -> EvidenceBody -> ANSWERS -> KeyQuestion
  Recommendation -> BASED_ON -> EvidenceBody -> INCLUDES -> Study
  ```
  Does the chain make clinical sense? Does the evidence body's topic match the recommendation's topic?

### Accuracy threshold

**Requirement: <10 flagged low-confidence links**

| Result | Action |
|--------|--------|
| <10 flagged, chains look correct | Proceed to graph population |
| 10-20 flagged | Review each, accept/reject, proceed |
| >20 flagged or broken chains | Investigate extraction quality, may need to re-extract or adjust confidence thresholds in YAML |

---

## Checkpoint D: After Graph Population (Final Review)

**Run command**:
```bash
python scripts/pipeline/run_pipeline.py --config configs/guidelines/diabetes-t2-2023.yaml \
  --start-from populate_graph
```

This populates Neo4j, generates embeddings, and runs automated validation.

### What to review

#### D1: Automated validation output

The `validate` stage prints results. Verify:

- [ ] **Node counts match expected**:
  - Guideline: 1
  - ClinicalModule: 9
  - Recommendation: 54
  - KeyQuestion: 12
  - EvidenceBody: 12
  - Study: ~103

- [ ] **Zero orphaned nodes** (every entity connected to at least one other entity)
- [ ] **All evidence chain traversals succeed**

#### D2: Neo4j Browser verification

Open Neo4j Browser at http://localhost:7474 and run these queries:

**Node count overview**:
```cypher
MATCH (n) RETURN labels(n)[0] AS NodeType, count(*) AS Count ORDER BY Count DESC
```

**Sample evidence chain** (pick any recommendation number):
```cypher
MATCH (r:Recommendation {rec_number: 8})-[:BASED_ON]->(eb:EvidenceBody)-[:INCLUDES]->(s:Study)
RETURN r.rec_text, eb.quality_rating, collect(s.title)
```

**Check for orphaned recommendations**:
```cypher
MATCH (r:Recommendation) WHERE NOT (r)-[:BASED_ON]->(:EvidenceBody) RETURN r.rec_number, r.topic
```

**Verify KQ coverage**:
```cypher
MATCH (kq:KeyQuestion)<-[:ANSWERS]-(eb:EvidenceBody)-[:INCLUDES]->(s:Study)
RETURN kq.kq_number, kq.question_text, count(DISTINCT s) AS study_count
ORDER BY kq.kq_number
```

- [ ] Node counts match expectations
- [ ] Evidence chain query returns results with study titles
- [ ] No orphaned recommendations (query returns empty)
- [ ] All 12 KQs have associated studies

#### D3: Embedding search (if OPENAI_API_KEY is set)

Test that vector search works:
```cypher
// First, get a query vector by embedding a test question
// (This requires the GenAI plugin and OPENAI_API_KEY)
CALL db.index.vector.queryNodes('recommendation_embedding', 5, $queryVector)
YIELD node, score
RETURN node.rec_text, score
```

Or use the test script:
```bash
python scripts/test_vector_search.py
```

- [ ] Vector search returns relevant recommendations
- [ ] Similarity scores are reasonable (>0.7 for clearly relevant queries)

### Final sign-off

| Check | Status |
|-------|--------|
| Node counts correct | [ ] |
| Zero orphans | [ ] |
| Evidence chains traversable | [ ] |
| All 12 KQs have studies | [ ] |
| Embedding search works | [ ] |

If all checks pass, the diabetes CPG is fully ingested and the graph is ready for Phase 3 (Query API).

---

## Quick Reference: Full Checkpoint Sequence

| Checkpoint | After stage | What to review | Threshold | Blocks |
|------------|-------------|---------------|-----------|--------|
| **A** | `preprocess` | Tables, document map, markdown | Tables match PDF | All extraction |
| **B1** | `extract_recommendations` | 10 random recommendations | >95% accuracy | KQ extraction |
| **B2** | `extract_key_questions` | All 12 KQs with PICOTS | 100% accuracy | Evidence extraction |
| **B3** | `extract_studies` + `fetch_metadata` | PMID resolution rate, evidence bodies | >90% PMIDs resolved | Relationship inference |
| **C** | `build_relationships` | Low-confidence links, orphans | <10 flagged | Graph population |
| **D** | `populate_graph` + `validate` | Node counts, traversals, embeddings | All pass | Phase 3 |

---

**Document Version**: 1.0
**Created**: February 4, 2026
