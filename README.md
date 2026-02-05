# HiGraph-CPG

Transforms VA/DoD Clinical Practice Guidelines (CPGs) from static PDFs into AI-queryable Neo4j knowledge graphs. Extracts structured clinical entities using LLMs, populates a typed graph database with evidence chains, and supports semantic search via vector embeddings.

The initial implementation targets the **Type 2 Diabetes Mellitus CPG** (54 recommendations, 12 key questions, 103 studies). The pipeline is configuration-driven: adding a new guideline requires only a YAML config file, no code changes.

## Architecture

```
PDF Source --> [PDF Preprocessing]  --> Structured JSON (tables, sections, TOC)
          --> [LLM Extraction]     --> Entity JSON (recommendations, KQs, studies, evidence)
          --> [PubMed Enrichment]  --> Enriched studies with abstracts + MeSH terms
          --> [Relationship Inference] --> Linked entities with confidence scores
          --> [Graph Population]   --> Neo4j nodes + relationships (MERGE, idempotent)
          --> [Embedding Generation] --> Vector-indexed nodes for semantic search
```

The graph structure replaces traditional RAG chunking. Instead of arbitrary text fragments, each node is a semantically meaningful clinical entity with typed relationships to other entities. See [tasks/extraction-strategy.md](tasks/extraction-strategy.md) for the full rationale.

## Prerequisites

- **Python 3.10+**
- **Neo4j 2025.11+** (Community Edition via Docker) with GenAI plugin and APOC Extended
- **Docker** and **Docker Compose**
- **API keys**: Anthropic (LLM extraction), OpenAI (embeddings via Neo4j GenAI plugin), PubMed (optional)

## Setup

### 1. Clone and install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

Create a `.env` file in the project root:

```bash
# LLM API (required for extraction)
ANTHROPIC_API_KEY=your_anthropic_key_here

# Neo4j (required for graph population)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here

# OpenAI (required for embeddings via Neo4j GenAI plugin)
OPENAI_API_KEY=your_openai_key_here

# PubMed (optional — increases rate limit from 3/sec to 10/sec)
PUBMED_API_KEY=your_pubmed_key_here
PUBMED_EMAIL=your_email@domain.com
```

### 3. Start Neo4j

```bash
docker-compose up -d
```

### 4. Initialize the graph schema

```bash
python scripts/init_schema.py
```

### 5. Place the source PDF

Put the guideline PDF at `docs/source-guidelines/VADOD-Diabetes-CPG_Final_508.pdf` (the pipeline checks this location automatically).

## Running the Pipeline

### Full pipeline

```bash
python scripts/pipeline/run_pipeline.py --config configs/guidelines/diabetes-t2-2023.yaml
```

### Run specific stages

```bash
# Preprocessing only
python scripts/pipeline/run_pipeline.py --config configs/guidelines/diabetes-t2-2023.yaml \
  --stop-after preprocess

# Extraction only (assumes preprocessing is done)
python scripts/pipeline/run_pipeline.py --config configs/guidelines/diabetes-t2-2023.yaml \
  --start-from extract_metadata --stop-after extract_studies

# Graph population only (assumes extraction is done)
python scripts/pipeline/run_pipeline.py --config configs/guidelines/diabetes-t2-2023.yaml \
  --start-from populate_graph

# Resume from a failed stage
python scripts/pipeline/run_pipeline.py --config configs/guidelines/diabetes-t2-2023.yaml \
  --start-from resolve_pmids
```

### List available stages

```bash
python scripts/pipeline/run_pipeline.py --config configs/guidelines/diabetes-t2-2023.yaml --list-stages
```

### Pipeline stages

| # | Stage | Description | Requires |
|---|-------|-------------|----------|
| 1 | `preprocess` | TOC extraction, table extraction, section splitting, markdown conversion | PDF |
| 2 | `extract_metadata` | Guideline + clinical modules from config | Config only |
| 3 | `extract_recommendations` | LLM extracts from recommendations table | ANTHROPIC_API_KEY |
| 4 | `extract_key_questions` | LLM extracts PICOTS from appendix | ANTHROPIC_API_KEY |
| 5 | `extract_evidence_bodies` | LLM extracts GRADE synthesis | ANTHROPIC_API_KEY |
| 6 | `extract_studies` | LLM parses reference citations | ANTHROPIC_API_KEY |
| 7 | `resolve_pmids` | PubMed PMID resolution | Internet |
| 8 | `fetch_metadata` | PubMed abstract/MeSH enrichment | Internet |
| 9 | `build_relationships` | Infer entity links with confidence scores | Extracted data |
| 10 | `populate_graph` | MERGE nodes + relationships into Neo4j | Running Neo4j |
| 11 | `generate_embeddings` | Vector embeddings via GenAI plugin | OPENAI_API_KEY + Neo4j |
| 12 | `validate` | Node counts, orphan checks, traversals | Running Neo4j |

## Adding a New Guideline

The pipeline is configuration-driven. To add a new VA/DoD CPG (e.g., Hypertension, CKD, COPD), follow these steps:

### Step 1: Examine the PDF

Open the new guideline PDF and identify the following sections and their page ranges:

| Section | What to look for | Example (Diabetes) |
|---------|------------------|--------------------|
| Recommendations table | The main table listing all recommendations with strength/direction | Pages 25-70 |
| Key questions (narrative) | Appendix with PICOTS descriptions for each key question | Pages 78-87 |
| Key questions (summary table) | Table listing KQ numbers, descriptions, and study counts | Pages 90-91 |
| Evidence tables | GRADE evidence ratings (quality, strength of evidence) | Pages 109-113 |
| References | Bibliography with numbered citations | Pages 150-165 |

Also note:
- The **exact column headers** in the recommendations table (e.g., "Strengtha" vs "Strength" — footnote markers vary)
- The **topic categories** used to group recommendations (e.g., "Pharmacotherapy", "Self-Management")
- The **total counts** of recommendations, key questions, and studies

### Step 2: Create a YAML config file

Copy the diabetes config as a template:

```bash
cp configs/guidelines/diabetes-t2-2023.yaml configs/guidelines/your-guideline-slug.yaml
```

Edit the new file. Every field in the `guideline` section needs updating:

```yaml
guideline:
  id: "CPG_HTN_2020"                    # Unique ID prefix for all entity IDs
  slug: "hypertension-2020"             # Used for directory names
  disease_condition: "Hypertension"
  version: "1.0"
  publication_date: "2020-10-01"
  organization: "VA/DoD"
  full_title: "VA/DoD Clinical Practice Guideline for the Diagnosis and Management of Hypertension"
  scope_description: "Management of hypertension in primary care"
  status: "Active"
```

Update `source` with the PDF filename:

```yaml
source:
  pdf_filename: "VADOD-Hypertension-CPG.pdf"
  total_pages: 200
```

Update `sections` with the page ranges you identified:

```yaml
sections:
  recommendations_table:
    start_page: 30
    end_page: 55
    table_name: "recommendations"
    column_mapping:
      "Topic": "topic"
      "Subtopic": "subtopic"
      "#": "rec_number"
      "Recommendation": "rec_text"
      "Strength": "strength_raw"           # Match the actual column header
      "Category": "category"               # Match the actual column header
    alt_column_names:                       # Any alternate headers found on different pages
      "Strengtha": "strength_raw"
  key_questions_picots:
    start_page: 60
    end_page: 70
  # ... fill in remaining sections
```

Update `modules` to reflect the topic groupings in this guideline:

```yaml
modules:
  - id_suffix: "MOD_SCREENING"
    name: "Screening and Diagnosis"
    topics: ["Screening", "Diagnosis"]
    sequence_order: 1
  - id_suffix: "MOD_TREATMENT"
    name: "Treatment"
    topics: ["Pharmacotherapy", "Lifestyle"]
    sequence_order: 2
  # ... add all topic modules
```

Update `expected_counts` with the totals you noted:

```yaml
expected_counts:
  recommendations: 40
  key_questions: 8
  studies: 85
  evidence_bodies: 8
```

### Step 3: Place the PDF

```bash
cp /path/to/your-guideline.pdf docs/source-guidelines/VADOD-Hypertension-CPG.pdf
```

The pipeline checks three locations for the PDF:
1. `data/guidelines/{slug}/source/{pdf_filename}`
2. `docs/source-guidelines/{pdf_filename}`
3. `data/source/{pdf_filename}`

### Step 4: Run the pipeline

```bash
python scripts/pipeline/run_pipeline.py --config configs/guidelines/your-guideline-slug.yaml
```

### Step 5: Review validation checkpoints

The pipeline has 4 manual quality gates:

| After stage | Review | Threshold |
|-------------|--------|-----------|
| `extract_recommendations` | 10 random samples | >95% accuracy |
| `extract_key_questions` | All KQs reviewed | 100% accuracy |
| `resolve_pmids` | PMID resolution rate | >90% resolved |
| `build_relationships` | Low-confidence links | <10 flagged |

Review files are saved to `data/guidelines/{slug}/manual_review/` and `data/guidelines/{slug}/validation/`.

If extraction accuracy is low, adjust the prompt templates in `scripts/extraction/templates/` or refine column mappings in your config, then re-run from the failed stage with `--start-from`.

## Project Structure

```
HiGraph-CPG/
├── configs/
│   └── guidelines/                 # One YAML config per guideline
│       └── diabetes-t2-2023.yaml
├── data/
│   └── guidelines/
│       └── diabetes-t2-2023/       # Per-guideline outputs (gitignored)
│           ├── source/             # PDF copy
│           ├── preprocessed/       # Tables, document map, sections
│           ├── extracted/          # LLM-extracted entity JSON
│           ├── checkpoints/        # Batch processing resume points
│           ├── manual_review/      # Flagged items for review
│           └── validation/         # Quality reports
├── docs/
│   ├── source-guidelines/          # Source PDFs
│   └── technical/
│       ├── SCHEMA.md               # Neo4j schema (17 node types)
│       ├── GRAPH_TRAVERSALS.md     # Cypher query patterns
│       └── EMBEDDING_STRATEGY.md   # Embedding approach
├── schema/
│   ├── node_types.json             # Node type definitions
│   ├── relationship_types.json     # Relationship definitions
│   └── constraints.cypher          # Uniqueness constraints
├── scripts/
│   ├── pipeline/                   # Orchestrator + config loader
│   ├── pdf_preprocessing/          # PDF parsing, table extraction
│   ├── extraction/                 # LLM-based entity extraction
│   │   └── templates/              # Prompt templates + schemas
│   ├── pubmed/                     # PubMed API integration
│   ├── relationships/              # Relationship inference
│   ├── graph_population/           # Neo4j population + validation
│   └── validation/                 # Data quality checks
├── tasks/
│   ├── extraction-strategy.md      # Pipeline design rationale
│   ├── prd-higraph-cpg-data-ingestion.md
│   └── project-overview.md
├── utils/
│   └── embeddings.py               # Neo4j GenAI embedding utilities
├── tests/
├── docker-compose.yml
├── requirements.txt
└── CLAUDE.md
```

## Key Documentation

| Document | Description |
|----------|-------------|
| [tasks/extraction-strategy.md](tasks/extraction-strategy.md) | Why knowledge graph over RAG, full pipeline architecture, configuration-driven design rationale |
| [docs/technical/SCHEMA.md](docs/technical/SCHEMA.md) | Complete Neo4j schema: 17 node types, properties, constraints, indexes |
| [docs/technical/GRAPH_TRAVERSALS.md](docs/technical/GRAPH_TRAVERSALS.md) | Cypher query patterns for evidence chains, clinical decisions, semantic search |
| [docs/technical/EMBEDDING_STRATEGY.md](docs/technical/EMBEDDING_STRATEGY.md) | Embedding approach: GenAI plugin, OpenAI, native cosine similarity |
| [scripts/README.md](scripts/README.md) | Detailed script usage, individual commands, troubleshooting |
| [tasks/project-overview.md](tasks/project-overview.md) | Full project plan across all phases |

## Graph Schema (Phase 2 Scope)

Phase 2 populates 6 of 17 node types with the evidence chain backbone:

```
Guideline
  └── PART_OF ── ClinicalModule
                    └── CONTAINS ── KeyQuestion
                                      └── LEADS_TO ── Recommendation
                    ANSWERS ── EvidenceBody
                                 └── BASED_ON ── Recommendation
                                 └── INCLUDES ── Study
```

Entity IDs are deterministic and guideline-scoped: `CPG_DM_2023_REC_001`, `CPG_DM_2023_KQ_005`, `CPG_DM_2023_STUDY_045`.

All graph population uses Cypher `MERGE` for idempotency (safe to re-run).

## Troubleshooting

**"Config file not found"** — Provide the full path: `--config configs/guidelines/diabetes-t2-2023.yaml`

**"PDF not found"** — Place the PDF at `docs/source-guidelines/{pdf_filename}` as specified in the YAML config.

**"API key not found"** — Set `ANTHROPIC_API_KEY` in the `.env` file at the project root.

**"Neo4j connection refused"** — Start Neo4j: `docker-compose up -d`

**LLM extraction errors** — Check `data/guidelines/{slug}/checkpoints/` for saved progress. The batch processor resumes automatically from the last checkpoint.

**Resuming after failure** — Use `--start-from <stage>` to resume from the failed stage without re-running earlier stages.
