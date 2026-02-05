# PRD: HiGraph-CPG Data Ingestion - Config-Driven Pipeline

## Overview

**Feature**: Config-driven extraction and ingestion of VA/DoD CPGs into Neo4j knowledge graph

**Description**: A reusable, configuration-driven pipeline that extracts clinical entities from any VA/DoD CPG PDF, validates data quality, and populates the Neo4j graph database. Each guideline is parameterized via a YAML config file (`configs/guidelines/<slug>.yaml`) — the pipeline code is generic. Initial target: Type 2 Diabetes Mellitus CPG (54 recommendations, 12 key questions, 103 studies).

**Problem**: Clinical practice guidelines exist as PDF documents. We need structured, machine-readable data in the graph database to enable AI-powered querying and decision support.

**Context**: This is Phase 2 of HiGraph-CPG. Phase 1 (foundation with schema and infrastructure) must be complete before starting this PRD.

**Implementation**: Config-driven pipeline implemented. See `tasks/extraction-strategy.md` for technical architecture. Run via `python scripts/pipeline/run_pipeline.py --config configs/guidelines/diabetes-t2-2023.yaml`.

---

## Resume Point (February 4, 2026)

All 48 pipeline scripts are written and syntax-verified. **No pipeline stages have been executed yet.** The next session should run the pipeline against the actual diabetes CPG PDF.

**Before running anything:**

1. Activate the virtual environment: `.\.venv\Scripts\Activate.ps1` (PowerShell) or `.\.venv\Scripts\activate.bat` (CMD)
2. Verify Neo4j is running: `docker-compose up -d`
3. Verify the PDF exists at `docs/source-guidelines/VADOD-Diabetes-CPG_Final_508.pdf`
4. Verify `.env` has `ANTHROPIC_API_KEY`, `NEO4J_*`, `OPENAI_API_KEY`, `PUBMED_API_KEY`

**Then follow the Next Steps section at the bottom of this document** — run stages incrementally with human review checkpoints between each group. **Do NOT skip the review checkpoints.** Each one prevents a specific class of error from compounding downstream.

**Key files for context:**

- `tasks/human-review-guide.md` — **Detailed instructions for each review checkpoint** (what to look at, what to compare against, pass/fail thresholds, what to do if it fails)
- `configs/guidelines/diabetes-t2-2023.yaml` — all page ranges, column mappings, expected counts
- `scripts/pipeline/run_pipeline.py` — 12-stage orchestrator (`--start-from` / `--stop-after`)
- `tasks/extraction-strategy.md` — full pipeline architecture and design rationale
- `README.md` — setup, usage, and "adding a new guideline" guide

---

## Working Backlog

### Phase 1: PDF Preprocessing & Structure Extraction

- [x] **STORY-01**: As a data engineer, I want the diabetes CPG PDF split into manageable sections so that I can process each section independently
  - **Priority**: Must-Have
  - **Status**: Scripts implemented, awaiting first pipeline run on actual PDF
  - **Acceptance Criteria**: (verified at Manual Testing checkpoint)
    - [ ] PDF split into 15-20 separate section files (recommendations, key questions, evidence tables, references, etc.)
    - [ ] Table of contents extracted with page number mappings
    - [ ] Each section saved as both PDF and markdown format
    - [ ] Document map JSON file created showing section boundaries
    - [ ] All critical tables (Table 5, Table A-2, Appendix E) extracted as structured JSON
  - **Tasks**:
    - [x] Backend: Create scripts/pdf_preprocessing/extract_toc.py to parse table of contents (refactored to config-driven)
    - [x] Backend: Create scripts/pdf_preprocessing/split_sections.py to extract sections by page range
    - [x] Backend: Create scripts/pdf_preprocessing/extract_tables.py using pdfplumber for table extraction (refactored to config-driven)
    - [x] Backend: Create scripts/pdf_preprocessing/convert_to_markdown.py using marker (with PyMuPDF fallback)
    - [x] Backend: Add required packages to requirements.txt (PyMuPDF, pdfplumber, marker-pdf)
    - [x] Backend: Create scripts/pdf_preprocessing/validate_extraction.py to verify all sections extracted
    - [x] Backend: Generate data directory structure for outputs (via PipelineContext)
    - [ ] Testing: Run preprocessing on diabetes CPG PDF, verify all sections present
    - [ ] Local Testing: Verify table structure preservation, markdown quality, section completeness
    - [ ] Manual Testing: CHECKPOINT — Review sample sections and table extractions
  - **Technical Notes**: Uses PyMuPDF for splitting, pdfplumber for tables, marker-pdf for markdown (falls back to PyMuPDF on Python 3.14). Config-driven: page ranges and column mappings come from YAML config. Data stored per-guideline at `data/guidelines/<slug>/preprocessed/`.
  - **Fallback Note**: If pdfplumber produces poor table extraction results during the first run, **Docling + Tesseract OCR** is a proven fallback for table extraction (validated separately with good results on clinical tables). The pipeline is modular — `extract_tables.py` just needs to output JSON with normalized column names, so the parsing tool can be swapped without touching downstream stages. See `tasks/extraction-strategy.md` "Resilience and Fallback Strategy" for full details.
  - **Blockers**: None (source PDF must be available)

- [x] **STORY-02**: As a data engineer, I want extraction templates and prompt engineering scripts so that AI can consistently extract structured data from each section
  - **Priority**: Must-Have
  - **Status**: All templates and schemas implemented
  - **Acceptance Criteria**: (verified at Manual Testing checkpoint)
    - [x] Extraction templates created for each entity type (recommendations, key questions, studies, evidence bodies)
    - [x] JSON schemas defined for each entity type output
    - [x] Prompt templates follow best practices (clear instructions, output format specification, extraction rules)
    - [ ] Test extraction runs on sample data produce valid JSON
    - [x] Batch size configurations optimized (5-10 recommendations per batch)
  - **Tasks**:
    - [x] Backend: Create scripts/extraction/templates/recommendation_template.py with prompt and JSON schema (refactored, parameterized)
    - [x] Backend: Create scripts/extraction/templates/key_question_template.py
    - [x] Backend: Create scripts/extraction/templates/study_template.py
    - [x] Backend: Create scripts/extraction/templates/evidence_body_template.py
    - [x] Backend: Create scripts/extraction/ai_client.py with LLM API integration (already existed, kept as-is)
    - [x] Backend: Create scripts/extraction/batch_processor.py for incremental extraction (already existed, kept as-is)
    - [x] Backend: Add jsonschema library to requirements.txt for validation
    - [x] Backend: Create scripts/extraction/validate_json.py to verify extracted data against schemas
    - [ ] Testing: Test each template with sample sections, verify JSON validity
    - [ ] Local Testing: Run extraction on 5-10 sample recommendations, verify structure and accuracy
    - [ ] Manual Testing: CHECKPOINT — Review extraction quality and template effectiveness
  - **Technical Notes**: All templates expose consistent interface: `create_extraction_prompt(data, config)`, `get_schema()`, `validate(item)`. Templates are parameterized by guideline config for reuse across CPGs.
  - **Blockers**: ~~STORY-01 must be complete~~ (resolved)

### Phase 2: Core Entity Extraction

- [x] **STORY-03**: As a guideline author, I want all 54 recommendations extracted from Table 5 with complete metadata so that the core clinical guidance is available in the graph
  - **Priority**: Must-Have
  - **Status**: Script implemented with batch processing and checkpoints, awaiting first run
  - **Acceptance Criteria**: (verified at Manual Testing checkpoint)
    - [ ] All 54 recommendations extracted from Table 5
    - [ ] Each recommendation has: rec_number, rec_text, strength, direction, topic, subtopic, category, page_number
    - [ ] Extraction accuracy >95% on validation sample (10 recommendations)
    - [ ] Data saved to data/guidelines/diabetes-t2-2023/extracted/recommendations.json
    - [ ] Checkpoint file saved after each batch for resume capability
    - [ ] Extraction report generated showing progress and any issues
  - **Tasks**:
    - [x] Backend: Create scripts/extraction/extract_recommendations.py using recommendation template
    - [x] Backend: Implement incremental processing (batch size from config, default 5)
    - [x] Backend: Add checkpoint saving after each batch to data/guidelines/<slug>/checkpoints/
    - [x] Backend: Create scripts/validation/validate_recommendations.py for quality checks
    - [x] Backend: Implement duplicate detection (same rec_number)
    - [x] Backend: Generate extraction report showing counts, issues, completion percentage
    - [ ] Testing: Extract all 54 recommendations, run validation script
    - [ ] Local Testing: Verify all required fields present, strength/direction values valid, no duplicates
    - [ ] Manual Testing: CHECKPOINT — Manually review 10 random recommendations for accuracy
  - **Technical Notes**: Table 5 spans pages 25-70 (configured in YAML). Strength values: "Strong", "Weak", "Neither for nor against". Direction values: "For", "Against", "Neither". Column mappings handle footnote markers (e.g., "Strengtha" -> "strength_raw").
  - **Blockers**: ~~STORY-01, STORY-02 must be complete~~ (resolved)

- [x] **STORY-04**: As a guideline author, I want all 12 Key Questions extracted with complete PICOTS elements so that the systematic review methodology is captured
  - **Priority**: Must-Have
  - **Status**: Script implemented, awaiting first run
  - **Acceptance Criteria**: (verified at Manual Testing checkpoint)
    - [ ] All 12 Key Questions extracted from Appendix A
    - [ ] Each KQ has: kq_number, question_text, PICOTS elements (population, intervention, comparator, outcomes_critical, outcomes_important, timing, setting)
    - [ ] Critical vs Important outcomes correctly categorized
    - [ ] Number of studies per KQ captured from Table A-2
    - [ ] Data saved to data/guidelines/diabetes-t2-2023/extracted/key_questions.json
    - [ ] 100% accuracy on manual review (only 12 items)
  - **Tasks**:
    - [x] Backend: Create scripts/extraction/extract_key_questions.py using key question template
    - [x] Backend: Extract PICOTS elements from structured sections in Appendix A
    - [x] Backend: Cross-reference with Table A-2 for study counts
    - [x] Backend: Parse outcomes lists distinguishing critical (7-9 rating) from important (4-6 rating)
    - [x] Backend: Create scripts/validation/validate_key_questions.py to check PICOTS completeness
    - [ ] Testing: Extract all 12 KQs, verify PICOTS structure
    - [ ] Local Testing: Verify all PICOTS fields present, outcomes categorized correctly
    - [ ] Manual Testing: CHECKPOINT — Review all 12 Key Questions for completeness and accuracy
  - **Technical Notes**: KQ sections in Appendix A (pp78-87) have clear PICOTS structure. Page ranges from config.
  - **Blockers**: ~~STORY-01, STORY-02 must be complete~~ (resolved)

### Phase 3: Study Metadata & Evidence Extraction

- [x] **STORY-05**: As a guideline author, I want all 103 studies extracted with metadata and PMIDs resolved so that the evidence base is complete and linkable
  - **Priority**: Must-Have
  - **Status**: Scripts implemented, PubMed API key verified working (10 req/sec)
  - **Acceptance Criteria**: (verified at Manual Testing checkpoint)
    - [ ] All 103 study citations extracted from References section (pp150-165)
    - [ ] PMIDs resolved via PubMed API for >90% of studies
    - [ ] Each study has: study_id, title, authors, journal, year, pmid, doi (when available)
    - [ ] Study types identified from references or document text
    - [ ] Unresolved PMIDs flagged for manual review
    - [ ] Data saved to data/guidelines/diabetes-t2-2023/extracted/studies.json
  - **Tasks**:
    - [x] Backend: Create scripts/extraction/extract_studies.py to parse references section
    - [x] Backend: Create scripts/pubmed/resolve_pmids.py using PubMed E-utilities API
    - [x] Backend: Implement citation parsing with AI extraction
    - [x] Backend: Add Bio.Entrez (Biopython) to requirements.txt for PubMed API
    - [x] Backend: Implement rate limiting (3 requests/sec without API key, 10/sec with key)
    - [x] Backend: Create scripts/pubmed/fetch_metadata.py to enrich with full PubMed data
    - [x] Backend: Flag unresolved citations to data/guidelines/<slug>/manual_review/
    - [x] Backend: Create scripts/validation/validate_studies.py to check completeness
    - [ ] Testing: Extract citations, resolve PMIDs, verify metadata enrichment
    - [ ] Local Testing: Verify PMID resolution rate >90%, check for duplicates, validate study metadata
    - [ ] Manual Testing: CHECKPOINT — Review unresolved PMIDs and sample study metadata
  - **Technical Notes**: PubMed API key obtained and verified. Cross-guideline cache at `data/shared/pubmed_cache/` avoids redundant API calls.
  - **Blockers**: ~~STORY-01, STORY-02 must be complete~~ (resolved)

- [x] **STORY-06**: As a guideline author, I want evidence bodies extracted for each Key Question with quality ratings so that evidence synthesis is captured
  - **Priority**: Should-Have
  - **Status**: Script implemented, awaiting first run
  - **Acceptance Criteria**: (verified at Manual Testing checkpoint)
    - [ ] Evidence body extracted for each of 12 Key Questions
    - [ ] Each evidence body has: evidence_id, kq_id, topic, quality_rating, num_studies, study_types, key_findings
    - [ ] GRADE quality ratings (High/Moderate/Low/Very Low) captured
    - [ ] Evidence synthesis text extracted from Appendix A sections
    - [ ] Data saved to data/guidelines/diabetes-t2-2023/extracted/evidence_bodies.json
  - **Tasks**:
    - [x] Backend: Create scripts/extraction/extract_evidence_bodies.py
    - [x] Backend: Extract evidence synthesis paragraphs from each KQ section in Appendix A
    - [x] Backend: Parse GRADE quality ratings from text
    - [x] Backend: Link to study counts from Table A-2
    - [x] Backend: Identify study types mentioned in each synthesis
    - [x] Backend: Create scripts/validation/validate_evidence_bodies.py
    - [ ] Testing: Extract evidence bodies for all 12 KQs, verify linkage to KQs
    - [ ] Local Testing: Verify quality ratings valid, all KQs have evidence body, findings captured
    - [ ] Manual Testing: CHECKPOINT — Review evidence synthesis accuracy
  - **Technical Notes**: Evidence synthesis in Appendix A follows each KQ. Quality ratings use GRADE methodology.
  - **Blockers**: ~~STORY-04 must be complete~~ (resolved)

### Phase 4: Relationship Building & Graph Population

- [x] **STORY-07**: As a data engineer, I want relationships automatically inferred and validated so that the knowledge graph is fully connected
  - **Priority**: Must-Have
  - **Status**: All relationship scripts implemented with confidence scoring
  - **Acceptance Criteria**: (verified at Manual Testing checkpoint)
    - [ ] Recommendation-to-KeyQuestion relationships built (54 recommendations -> 12 KQs)
    - [ ] KeyQuestion-to-EvidenceBody relationships built (12 KQs -> 12 evidence bodies)
    - [ ] EvidenceBody-to-Study relationships built (12 evidence bodies -> 103 studies)
    - [ ] Recommendation-to-EvidenceBody relationships inferred (54 recs -> evidence)
    - [ ] Confidence scores assigned to inferred relationships
    - [ ] Low-confidence relationships (<0.8) flagged for manual review
    - [ ] Relationships saved to data/guidelines/<slug>/extracted/relationships.json
  - **Tasks**:
    - [x] Backend: Create scripts/relationships/link_recommendations_to_kqs.py
    - [x] Backend: Implement strategy 1: Extract KQ number mentions from recommendation text
    - [x] Backend: Implement strategy 2: Topic-based matching using TF-IDF text similarity (scikit-learn)
    - [x] Backend: Combine strategies with weighted confidence scoring algorithm
    - [x] Backend: Create scripts/relationships/link_kqs_to_evidence.py (direct 1:1 mapping by kq_number)
    - [x] Backend: Create scripts/relationships/link_evidence_to_studies.py (reference number matching)
    - [x] Backend: Create scripts/relationships/build_all_relationships.py (aggregator + structural rels)
    - [x] Backend: Flag low-confidence links to data/guidelines/<slug>/manual_review/
    - [x] Backend: Create scripts/validation/validate_relationships.py to check completeness
    - [ ] Testing: Build all relationships, verify no orphaned nodes
    - [ ] Local Testing: Check relationship counts, verify confidence scores, identify orphans
    - [ ] Manual Testing: CHECKPOINT — Review low-confidence relationships and validate sample chains
  - **Technical Notes**: Confidence thresholds configurable in YAML: >0.8 auto-accept, 0.5-0.8 flagged, <0.5 excluded. Also builds structural relationships: PART_OF (Module->Guideline), CONTAINS (Module->KQ), BASED_ON (Rec->EvidenceBody).
  - **Blockers**: ~~STORY-03, STORY-04, STORY-05, STORY-06 must be complete~~ (resolved)

- [x] **STORY-08**: As a guideline author, I want all extracted data populated into Neo4j with complete relationship mapping so that the knowledge graph is queryable
  - **Priority**: Must-Have
  - **Status**: All population scripts implemented with MERGE idempotency
  - **Acceptance Criteria**: (verified at Manual Testing checkpoint)
    - [ ] All 54 recommendations created as nodes in Neo4j
    - [ ] All 12 key questions created as nodes
    - [ ] All 103 studies created as nodes
    - [ ] All 12 evidence bodies created as nodes
    - [ ] 1 Guideline + N ClinicalModule nodes created
    - [ ] All relationships created (BASED_ON, ANSWERS, INCLUDES, LEADS_TO, PART_OF, CONTAINS)
    - [ ] Node counts match expected: 54 recommendations, 12 KQs, 103 studies, 12 evidence bodies
    - [ ] Automated validation queries confirm no orphaned nodes
    - [ ] Graph browser visualization shows connected graph structure
  - **Tasks**:
    - [x] Backend: Create scripts/graph_population/neo4j_client.py (shared connection, MERGE helpers)
    - [x] Backend: Create scripts/graph_population/populate_guideline.py
    - [x] Backend: Create scripts/graph_population/populate_clinical_modules.py
    - [x] Backend: Create scripts/graph_population/populate_recommendations.py
    - [x] Backend: Create scripts/graph_population/populate_key_questions.py
    - [x] Backend: Create scripts/graph_population/populate_studies.py
    - [x] Backend: Create scripts/graph_population/populate_evidence_bodies.py
    - [x] Backend: Create scripts/graph_population/populate_relationships.py
    - [x] Backend: Implement MERGE-based idempotency (safe to re-run)
    - [x] Backend: Create scripts/graph_population/generate_embeddings.py (separate stage)
    - [x] Backend: Create scripts/graph_population/validate_graph.py with validation queries
    - [ ] Testing: Populate Neo4j from extracted data, run validation queries
    - [ ] Local Testing: Verify node counts, check for orphans, test sample traversals from GRAPH_TRAVERSALS.md
    - [ ] Manual Testing: CHECKPOINT — Review graph in Neo4j Browser and verify sample queries work
  - **Technical Notes**: All population uses Cypher MERGE keyed on entity IDs (`CPG_DM_2023_REC_001`). Entity IDs are deterministic and guideline-scoped. Embedding generation is a separate pipeline stage using Neo4j GenAI plugin + OpenAI text-embedding-3-small.
  - **Blockers**: ~~STORY-07 must be complete, Phase 1 (Neo4j infrastructure) must be operational~~ (resolved)

### Additional Infrastructure (Not in original PRD, implemented as part of config-driven architecture)

- [x] **INFRA-01**: Pipeline config system
  - [x] Created `configs/guidelines/diabetes-t2-2023.yaml` with page ranges, column mappings, modules, expected counts
  - [x] Created `scripts/pipeline/config_loader.py` — loads YAML, validates, returns typed dataclasses
  - [x] Created `scripts/pipeline/pipeline_context.py` — resolves all file paths, generates entity IDs
  - [x] Added pyyaml to requirements.txt

- [x] **INFRA-02**: Pipeline orchestrator
  - [x] Created `scripts/pipeline/run_pipeline.py` — 12-stage orchestrator with `--start-from` / `--stop-after`
  - [x] Created `scripts/extraction/extract_guideline_metadata.py` — generates guideline.json + clinical_modules.json from config (no LLM)

- [x] **INFRA-03**: Documentation
  - [x] Created `tasks/extraction-strategy.md` — pipeline design rationale and architecture
  - [x] Created project root `README.md` with setup, usage, and "adding a new guideline" guide
  - [x] Updated `scripts/README.md` for config-driven pipeline
  - [x] Updated `CLAUDE.md` with all new commands and architecture
  - [x] Set up Python virtual environment (`.venv/`)

---

## Non-Goals

- **Extraction of interventions, benefits, adverse events** (requires deeper domain knowledge, future enhancement)
- **Patient population and characteristic entities** (extract from narrative text, future phase)
- **Clinical scenarios** (require synthesis across recommendations, future phase)
- **Decision frameworks** (GRADE reasoning extraction, future enhancement)
- **Contraindications** (scattered throughout text, future extraction)
- **Automated continuous monitoring** (future Phase 8)
- **Multi-guideline ingestion** (focus on diabetes only, extend in Phase 6)

---

## Dependencies

### Internal

- Phase 1 (Foundation) complete with Neo4j running and schema defined
- Python 3.10+ environment (3.14 works except marker-pdf)
- Neo4j Python driver installed
- Virtual environment at `.venv/`

### External

- VA/DoD Type 2 Diabetes CPG PDF (165 pages, May 2023 version)
- PubMed E-utilities API access (API key obtained, 10 req/sec)
- LLM API access (Claude or GPT-4) with API key
- PDF processing libraries (PyMuPDF, pdfplumber; marker-pdf optional)

---

## Success Metrics

- [ ] All 54 recommendations extracted and loaded (100%)
- [ ] All 12 Key Questions extracted and loaded (100%)
- [ ] >90% of 103 studies have PMIDs resolved
- [ ] >95% extraction accuracy on validation samples
- [ ] <10 relationships flagged for manual review
- [ ] Zero orphaned nodes in graph (all entities connected)
- [ ] All example queries from GRAPH_TRAVERSALS.md execute successfully

---

## Open Questions

1. **LLM Provider**: Should we use Claude 3.5 Sonnet (best accuracy) or GPT-4 (faster, cheaper) for extraction?
   - **Recommendation**: Start with Claude 3.5 Sonnet, measure cost, switch if budget constrained

2. ~~**PubMed API Key**: Should we obtain official API key for 10 req/sec vs 3 req/sec?~~
   - **Resolved**: API key obtained and verified working (10 req/sec)

3. **Manual Review Process**: Who performs validation at checkpoints?
   - **Decision needed**: Clinical SME for recommendation accuracy, data engineer for technical completeness

4. **Unresolved PMIDs**: What's the process for manually resolving citations without PMIDs?
   - **Recommendation**: Create spreadsheet of unresolved, SME provides PMIDs or marks as grey literature

5. **Relationship Confidence Threshold**: Is 0.8 the right threshold for auto-accept?
   - **Can adjust after first run**, evaluate false positive/negative rate. Configurable in YAML.

---

## Appendix

### Directory Structure (Implemented)

```
HiGraph-CPG/
├── configs/
│   └── guidelines/
│       └── diabetes-t2-2023.yaml       # Guideline-specific config
├── data/
│   └── guidelines/
│       └── diabetes-t2-2023/           # Per-guideline outputs (gitignored)
│           ├── source/                 # PDF copy
│           ├── preprocessed/           # Document map, tables, sections, markdown
│           ├── extracted/              # LLM-extracted entity JSON
│           ├── checkpoints/            # Batch processing resume points
│           ├── manual_review/          # Flagged items for review
│           └── validation/             # Quality reports
│   └── shared/
│       └── pubmed_cache/               # Cross-guideline PubMed cache
├── scripts/
│   ├── pipeline/
│   │   ├── config_loader.py            # Load + validate YAML configs
│   │   ├── pipeline_context.py         # Resolve all file paths from config
│   │   └── run_pipeline.py             # 12-stage orchestrator
│   ├── pdf_preprocessing/
│   │   ├── extract_toc.py              # Config-driven TOC extraction
│   │   ├── split_sections.py           # Split PDF by config page ranges
│   │   ├── extract_tables.py           # Config-driven table extraction
│   │   ├── convert_to_markdown.py      # marker-pdf with PyMuPDF fallback
│   │   └── validate_extraction.py      # Verify preprocessing outputs
│   ├── extraction/
│   │   ├── templates/
│   │   │   ├── recommendation_template.py
│   │   │   ├── key_question_template.py
│   │   │   ├── study_template.py
│   │   │   └── evidence_body_template.py
│   │   ├── ai_client.py               # Unified LLM client (Claude/GPT-4)
│   │   ├── batch_processor.py          # Batch processing with checkpoints
│   │   ├── validate_json.py            # Generic JSON schema validation
│   │   ├── extract_guideline_metadata.py  # From config (no LLM)
│   │   ├── extract_recommendations.py
│   │   ├── extract_key_questions.py
│   │   ├── extract_evidence_bodies.py
│   │   └── extract_studies.py
│   ├── pubmed/
│   │   ├── resolve_pmids.py            # PMID resolution with rate limiting
│   │   └── fetch_metadata.py           # Abstract/MeSH enrichment
│   ├── relationships/
│   │   ├── link_recommendations_to_kqs.py
│   │   ├── link_kqs_to_evidence.py
│   │   ├── link_evidence_to_studies.py
│   │   └── build_all_relationships.py  # Aggregator + structural rels
│   ├── graph_population/
│   │   ├── neo4j_client.py             # Shared connection + MERGE helpers
│   │   ├── populate_guideline.py
│   │   ├── populate_clinical_modules.py
│   │   ├── populate_recommendations.py
│   │   ├── populate_key_questions.py
│   │   ├── populate_studies.py
│   │   ├── populate_evidence_bodies.py
│   │   ├── populate_relationships.py
│   │   ├── generate_embeddings.py      # Embed via Neo4j GenAI plugin
│   │   └── validate_graph.py           # Node counts, orphans, traversals
│   └── validation/
│       ├── validate_recommendations.py
│       ├── validate_key_questions.py
│       ├── validate_studies.py
│       ├── validate_evidence_bodies.py
│       └── validate_relationships.py
└── requirements.txt
```

### Current requirements.txt

```
PyMuPDF>=1.23.0          # PDF operations, splitting
pdfplumber>=0.10.0       # Table extraction
# marker-pdf>=0.2.0      # Optional, requires Python <=3.13
jsonschema>=4.20.0       # JSON validation
python-dotenv>=1.0.0     # Environment variable management
pyyaml>=6.0.0            # Pipeline configuration
anthropic>=0.7.0         # Claude API
biopython>=1.81          # PubMed E-utilities
neo4j>=5.14.0            # Neo4j Python driver
scikit-learn>=1.3.0      # Text similarity for relationship inference
numpy>=1.24.0            # Required by scikit-learn, biopython
pytest>=7.0.0            # Test framework
tqdm>=4.66.0             # Progress bars
```

---

## Next Steps

All backend scripts are implemented. The next milestone is running the pipeline end-to-end on the diabetes CPG PDF. **Each step requires a human review before proceeding to the next.** See `tasks/human-review-guide.md` for detailed review instructions at each checkpoint.

### Step 1: Preprocessing

```bash
python scripts/pipeline/run_pipeline.py --config configs/guidelines/diabetes-t2-2023.yaml --stop-after preprocess
```

**STOP — Human Review (Checkpoint A)**: Open the extracted tables and compare against the PDF. Verify Table 5 rows look correct, column names are recognized, and markdown sections are readable. This catches PDF parsing errors before spending LLM API credits. See `tasks/human-review-guide.md` Checkpoint A for detailed instructions.

### Step 2: Recommendation Extraction

```bash
python scripts/pipeline/run_pipeline.py --config configs/guidelines/diabetes-t2-2023.yaml \
  --start-from extract_metadata --stop-after extract_recommendations
```

**STOP — Human Review (Checkpoint B1)**: Sample 10 random recommendations from the JSON output. Compare each against the PDF. Verify rec_text is verbatim, strength/direction are correct, topics match. Requirement: >95% accuracy. See `tasks/human-review-guide.md` Checkpoint B1.

### Step 3: Key Question Extraction

```bash
python scripts/pipeline/run_pipeline.py --config configs/guidelines/diabetes-t2-2023.yaml \
  --start-from extract_key_questions --stop-after extract_key_questions
```

**STOP — Human Review (Checkpoint B2)**: Review all 12 key questions. Verify PICOTS elements are complete and accurate. Requirement: 100% accuracy. See `tasks/human-review-guide.md` Checkpoint B2.

### Step 4: Evidence Body + Study Extraction + PubMed

```bash
python scripts/pipeline/run_pipeline.py --config configs/guidelines/diabetes-t2-2023.yaml \
  --start-from extract_evidence_bodies --stop-after fetch_metadata
```

**STOP — Human Review (Checkpoint B3)**: Check evidence body count (12), GRADE ratings, PMID resolution rate (>90%), and spot-check 5 resolved PMIDs on PubMed. See `tasks/human-review-guide.md` Checkpoint B3.

### Step 5: Relationship Inference

```bash
python scripts/pipeline/run_pipeline.py --config configs/guidelines/diabetes-t2-2023.yaml \
  --start-from build_relationships --stop-after build_relationships
```

**STOP — Human Review (Checkpoint C)**: Review low-confidence links in `manual_review/`. Trace 2-3 sample evidence chains end-to-end. Requirement: <10 flagged items. See `tasks/human-review-guide.md` Checkpoint C.

### Step 6: Graph Population + Validation

```bash
python scripts/pipeline/run_pipeline.py --config configs/guidelines/diabetes-t2-2023.yaml \
  --start-from populate_graph
```

**STOP — Human Review (Checkpoint D)**: Verify node counts in Neo4j Browser, run sample traversal queries, test embedding search. See `tasks/human-review-guide.md` Checkpoint D.

---

**Document Version**: 2.0
**Created**: February 4, 2026
**Last Updated**: February 4, 2026
**Status**: Implementation Complete — Awaiting First Pipeline Run
