# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this project.

## Project Overview

HiGraph-CPG transforms static VA/DoD Clinical Practice Guidelines (CPGs) into AI-queryable Neo4j knowledge graphs. The system uses a **config-driven pipeline** — each guideline is parameterized via a YAML config file, so the same extraction code handles any VA/DoD CPG. The initial implementation targets the Type 2 Diabetes Mellitus CPG (54 recommendations, 12 key questions, 103 studies).

## Tech Stack

- **Python 3.10+** — all scripts
- **Neo4j 2025.11+** (Community Edition via Docker) — graph database with native vector search
- **Neo4j GenAI plugin** — server-side embeddings via `genai.vector.encodeBatch()` calling OpenAI
- **OpenAI `text-embedding-3-small`** — 1536-dimension embeddings (via GenAI plugin, not Python SDK)
- **APOC Extended** — utility procedures for Neo4j
- **Claude 3.5 Sonnet** (primary LLM) / GPT-4 (alternative) — entity extraction
- **pdfplumber** — table extraction from PDFs; **PyMuPDF** — PDF operations; **marker-pdf** — PDF-to-markdown
- **PyYAML** — pipeline configuration files
- **Cypher** — graph query language (see `docs/technical/GRAPH_TRAVERSALS.md`)
- **Native `vector.similarity.cosine()`** — built-in Cypher function for similarity (no GDS library needed)

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Neo4j (start/stop)
docker-compose up -d          # Start Neo4j
docker-compose down            # Stop Neo4j (data persists in neo4j/ volume)

# Initialize schema (requires running Neo4j)
python scripts/init_schema.py

# ============================================================
# CONFIG-DRIVEN PIPELINE (Phase 2)
# All extraction scripts accept --config <path-to-yaml>
# ============================================================

# Run full pipeline for a guideline
python scripts/pipeline/run_pipeline.py --config configs/guidelines/diabetes-t2-2023.yaml

# Run specific stages
python scripts/pipeline/run_pipeline.py --config configs/guidelines/diabetes-t2-2023.yaml \
  --start-from extract_metadata --stop-after extract_studies

# List available pipeline stages
python scripts/pipeline/run_pipeline.py --config configs/guidelines/diabetes-t2-2023.yaml --list-stages

# Individual preprocessing scripts
python scripts/pdf_preprocessing/extract_toc.py --config configs/guidelines/diabetes-t2-2023.yaml
python scripts/pdf_preprocessing/extract_tables.py --config configs/guidelines/diabetes-t2-2023.yaml
python scripts/pdf_preprocessing/split_sections.py --config configs/guidelines/diabetes-t2-2023.yaml
python scripts/pdf_preprocessing/convert_to_markdown.py --config configs/guidelines/diabetes-t2-2023.yaml

# Entity extraction (requires ANTHROPIC_API_KEY in .env)
python scripts/extraction/extract_guideline_metadata.py --config configs/guidelines/diabetes-t2-2023.yaml
python scripts/extraction/extract_recommendations.py --config configs/guidelines/diabetes-t2-2023.yaml
python scripts/extraction/extract_key_questions.py --config configs/guidelines/diabetes-t2-2023.yaml
python scripts/extraction/extract_evidence_bodies.py --config configs/guidelines/diabetes-t2-2023.yaml
python scripts/extraction/extract_studies.py --config configs/guidelines/diabetes-t2-2023.yaml

# PubMed enrichment
python scripts/pubmed/resolve_pmids.py --config configs/guidelines/diabetes-t2-2023.yaml
python scripts/pubmed/fetch_metadata.py --config configs/guidelines/diabetes-t2-2023.yaml

# Relationship inference
python scripts/relationships/build_all_relationships.py --config configs/guidelines/diabetes-t2-2023.yaml

# Neo4j population (requires running Neo4j)
python scripts/graph_population/populate_guideline.py --config configs/guidelines/diabetes-t2-2023.yaml
python scripts/graph_population/populate_recommendations.py --config configs/guidelines/diabetes-t2-2023.yaml
python scripts/graph_population/generate_embeddings.py --config configs/guidelines/diabetes-t2-2023.yaml

# Validation
python scripts/graph_population/validate_graph.py --config configs/guidelines/diabetes-t2-2023.yaml
python scripts/validation/validate_recommendations.py --config configs/guidelines/diabetes-t2-2023.yaml

# ============================================================
# PHASE 1 SCRIPTS (still available)
# ============================================================

# Seed test data and run example traversals
python scripts/run_traversals.py            # seed + run, keep data
python scripts/run_traversals.py --cleanup  # seed + run + clean up

# Test vector search (requires OPENAI_API_KEY)
python scripts/test_vector_search.py

# Run tests
pytest tests/test_traversals.py -v
```

## Environment Variables

Required in `.env` at project root (see `.env.example`):

```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=...
OPENAI_API_KEY=...             # For embeddings via Neo4j GenAI plugin
ANTHROPIC_API_KEY=...          # For LLM extraction (Claude)
PUBMED_API_KEY=...             # optional, increases PubMed rate limit
PUBMED_EMAIL=...               # optional
```

## Architecture

### Config-Driven Pipeline

Every guideline gets a YAML config at `configs/guidelines/<slug>.yaml` specifying PDF path, section page ranges, table column mappings, expected entity counts, and guideline metadata. The pipeline code is generic; the config is guideline-specific.

**What varies per guideline**: PDF location, page ranges, table headers, entity counts, topic categories
**What stays the same**: LLM extraction pattern, Neo4j schema, graph population, PubMed resolution, validation, embedding generation

### Data Pipeline Stages

```
PDF Source
  → [preprocess]           TOC, tables, section split, markdown
  → [extract_metadata]     Guideline + clinical modules (from config, no LLM)
  → [extract_*]            LLM extraction with checkpoints
  → [resolve_pmids]        PubMed PMID resolution
  → [fetch_metadata]       PubMed abstract/MeSH enrichment
  → [build_relationships]  Confidence-scored entity links
  → [populate_graph]       MERGE nodes + relationships into Neo4j
  → [generate_embeddings]  Vector embeddings via GenAI plugin
  → [validate]             Node counts, orphans, traversals
```

### Script Organization

- **`scripts/pipeline/`** — Config loading, path resolution, orchestrator
- **`scripts/pdf_preprocessing/`** — PDF parsing: TOC, section split, table extraction, markdown
- **`scripts/extraction/`** — LLM-based extraction with templates (`templates/`), batch processor, AI client
- **`scripts/pubmed/`** — PubMed API: PMID resolution, metadata enrichment, cross-guideline caching
- **`scripts/relationships/`** — Entity linking with topic matching, text similarity, confidence scoring
- **`scripts/graph_population/`** — Neo4j MERGE-based population, embedding generation, validation
- **`scripts/validation/`** — Per-entity-type data quality validation

### LLM Integration Pattern

`ai_client.py` wraps Claude/GPT-4 with automatic retry (exponential backoff), rate limit handling, and JSON parsing with error recovery. `batch_processor.py` provides incremental processing with checkpoints saved per-guideline — extraction can resume after interruption.

### Neo4j Schema (17 node types)

Fully specified in `docs/technical/SCHEMA.md`. Phase 2 populates 6 of 17 node types:

**Phase 2 entities**: Guideline, ClinicalModule, Recommendation, KeyQuestion, EvidenceBody, Study
**Phase 2 relationships**: PART_OF, CONTAINS, LEADS_TO, BASED_ON, ANSWERS, INCLUDES

**Deferred to Phase 3+**: Intervention, Benefit, AdverseEvent, ClinicalScenario, PatientPopulation, PatientCharacteristic, Contraindication, Outcome, OutcomeMeasurement, QualityAssessment, DecisionFramework

Query patterns with Cypher examples are in `docs/technical/GRAPH_TRAVERSALS.md`.

### Data Directory Structure

```
data/
├── guidelines/
│   └── diabetes-t2-2023/          # slug from config
│       ├── source/                # PDF
│       ├── preprocessed/          # document map, tables, sections
│       │   ├── tables/
│       │   └── sections/
│       ├── extracted/             # LLM-extracted entities (JSON)
│       ├── checkpoints/           # Batch processing resume points
│       ├── manual_review/         # Flagged items
│       └── validation/            # Quality reports
├── shared/
│   └── pubmed_cache/              # Cross-guideline PMID cache
configs/
└── guidelines/
    └── diabetes-t2-2023.yaml      # Guideline-specific config
```

## Key Documentation

- **`docs/technical/SCHEMA.md`** — Complete Neo4j schema with all 17 node types, properties, constraints, and indexes
- **`docs/technical/GRAPH_TRAVERSALS.md`** — Cypher query patterns for evidence chains, clinical decision support, benefit-harm analysis, contraindication checking, and semantic search
- **`docs/technical/EMBEDDING_STRATEGY.md`** — Embedding approach rationale: GenAI plugin + OpenAI, native cosine similarity, Community Edition considerations
- **`tasks/extraction-strategy.md`** — Pipeline architecture, config-driven design, entity extraction approach
- **`tasks/project-overview.md`** — Full project plan across 8 phases
- **`tasks/prd-higraph-cpg-foundation.md`** — Phase 1 PRD: infrastructure and schema
- **`tasks/prd-higraph-cpg-data-ingestion.md`** — Phase 2 PRD: data extraction pipeline
- **`scripts/README.md`** — Detailed extraction script usage and troubleshooting

## Domain Context

The source document is the VA/DoD Type 2 Diabetes Mellitus CPG (May 2023, 165 pages). Critical data lives in:
- **Table 5** (pages 25-70): All 54 recommendations with strength/direction
- **Table A-2** (pages 90-91): 12 key questions with study counts
- **Appendix E** (pages 109-113): GRADE evidence ratings

Recommendations use GRADE methodology with strength ("Strong", "Weak", "Neither for nor against") and direction ("For", "Against", "Neither"). Extraction templates in `scripts/extraction/templates/` encode these enums and validation rules.

## Validation Checkpoints

The extraction pipeline has 4 manual quality gates:
1. **Recommendations**: 10 random samples, >95% accuracy required
2. **Key Questions**: All 12 reviewed, 100% accuracy required
3. **Study Linking**: >90% PMID resolution required
4. **Relationships**: <10 flagged items allowed
