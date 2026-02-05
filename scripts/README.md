# HiGraph-CPG Extraction Scripts

This directory contains scripts for the config-driven CPG-to-Knowledge-Graph pipeline. Each guideline is parameterized via a YAML config file — no code changes needed to add a new guideline.

## Directory Structure

```
scripts/
├── pipeline/                  # Pipeline infrastructure
│   ├── config_loader.py       # Load + validate YAML configs
│   ├── pipeline_context.py    # Resolve all file paths from config
│   └── run_pipeline.py        # Single entry point orchestrator
├── pdf_preprocessing/         # PDF parsing and structure extraction
│   ├── extract_toc.py         # Extract TOC, create document map
│   ├── split_sections.py      # Split PDF into section PDFs
│   ├── extract_tables.py      # Config-driven table extraction
│   ├── convert_to_markdown.py # Section PDFs -> markdown
│   └── validate_extraction.py # Verify preprocessing outputs
├── extraction/                # AI-powered data extraction
│   ├── templates/             # Extraction prompts and schemas
│   │   ├── recommendation_template.py
│   │   ├── key_question_template.py
│   │   ├── study_template.py
│   │   └── evidence_body_template.py
│   ├── ai_client.py           # LLM API wrapper (Claude/GPT-4)
│   ├── batch_processor.py     # Batch processing with checkpoints
│   ├── validate_json.py       # Generic JSON schema validation
│   ├── extract_guideline_metadata.py  # Guideline + modules from config
│   ├── extract_recommendations.py
│   ├── extract_key_questions.py
│   ├── extract_evidence_bodies.py
│   └── extract_studies.py
├── pubmed/                    # PubMed API integration
│   ├── resolve_pmids.py       # Resolve citations to PMIDs
│   └── fetch_metadata.py      # Fetch abstracts, MeSH terms
├── relationships/             # Relationship inference
│   ├── link_recommendations_to_kqs.py
│   ├── link_kqs_to_evidence.py
│   ├── link_evidence_to_studies.py
│   └── build_all_relationships.py  # Aggregator + structural rels
├── graph_population/          # Neo4j population
│   ├── neo4j_client.py        # Shared connection + MERGE helpers
│   ├── populate_guideline.py
│   ├── populate_clinical_modules.py
│   ├── populate_recommendations.py
│   ├── populate_key_questions.py
│   ├── populate_studies.py
│   ├── populate_evidence_bodies.py
│   ├── populate_relationships.py
│   ├── generate_embeddings.py # Embed node text via GenAI plugin
│   └── validate_graph.py     # Node counts, orphan checks, traversals
└── validation/                # Data quality validation
    ├── validate_recommendations.py
    ├── validate_key_questions.py
    ├── validate_studies.py
    ├── validate_evidence_bodies.py
    └── validate_relationships.py
```

## Quick Start

### Run the full pipeline for a guideline:

```bash
python scripts/pipeline/run_pipeline.py --config configs/guidelines/diabetes-t2-2023.yaml
```

### Run specific stages:

```bash
# Just preprocessing
python scripts/pipeline/run_pipeline.py --config configs/guidelines/diabetes-t2-2023.yaml \
  --stop-after preprocess

# Just extraction (assumes preprocessing done)
python scripts/pipeline/run_pipeline.py --config configs/guidelines/diabetes-t2-2023.yaml \
  --start-from extract_metadata --stop-after extract_studies

# Just graph population (assumes extraction done)
python scripts/pipeline/run_pipeline.py --config configs/guidelines/diabetes-t2-2023.yaml \
  --start-from populate_graph

# Resume from a failed stage
python scripts/pipeline/run_pipeline.py --config configs/guidelines/diabetes-t2-2023.yaml \
  --start-from resolve_pmids
```

### List available stages:

```bash
python scripts/pipeline/run_pipeline.py --config configs/guidelines/diabetes-t2-2023.yaml --list-stages
```

### Run individual scripts:

```bash
# Preprocessing
python scripts/pdf_preprocessing/extract_toc.py --config configs/guidelines/diabetes-t2-2023.yaml
python scripts/pdf_preprocessing/extract_tables.py --config configs/guidelines/diabetes-t2-2023.yaml

# Extraction (requires ANTHROPIC_API_KEY)
python scripts/extraction/extract_recommendations.py --config configs/guidelines/diabetes-t2-2023.yaml

# PubMed (optional PUBMED_API_KEY)
python scripts/pubmed/resolve_pmids.py --config configs/guidelines/diabetes-t2-2023.yaml

# Relationships
python scripts/relationships/build_all_relationships.py --config configs/guidelines/diabetes-t2-2023.yaml

# Graph population (requires running Neo4j)
python scripts/graph_population/validate_graph.py --config configs/guidelines/diabetes-t2-2023.yaml
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

Create a `.env` file in the project root:

```bash
# LLM API
ANTHROPIC_API_KEY=your_anthropic_key_here

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here

# OpenAI (for embeddings via Neo4j GenAI plugin)
OPENAI_API_KEY=your_openai_key_here

# PubMed (optional, increases rate limit from 3/sec to 10/sec)
PUBMED_API_KEY=your_pubmed_key_here
PUBMED_EMAIL=your_email@domain.com
```

### 3. Place Source PDF

The PDF should be at `docs/source-guidelines/VADOD-Diabetes-CPG_Final_508.pdf` (the pipeline looks there automatically).

## Adding a New Guideline

1. Open the PDF and identify section page ranges
2. Copy `configs/guidelines/diabetes-t2-2023.yaml` as a template
3. Fill in guideline metadata, page ranges, column mappings, expected counts
4. Run: `python scripts/pipeline/run_pipeline.py --config configs/guidelines/your-new-guideline.yaml`
5. Review validation checkpoints

No code changes needed — the pipeline adapts from the YAML config.

## Pipeline Stages

| Stage | Description | Requires |
|-------|-------------|----------|
| `preprocess` | TOC, tables, section split, markdown | PDF |
| `extract_metadata` | Guideline + clinical modules from config | Config only |
| `extract_recommendations` | LLM extracts from Table 5 | ANTHROPIC_API_KEY |
| `extract_key_questions` | LLM extracts PICOTS from Appendix A | ANTHROPIC_API_KEY |
| `extract_evidence_bodies` | LLM extracts GRADE synthesis | ANTHROPIC_API_KEY |
| `extract_studies` | LLM parses references | ANTHROPIC_API_KEY |
| `resolve_pmids` | PubMed PMID resolution | Internet |
| `fetch_metadata` | PubMed abstract/MeSH enrichment | Internet |
| `build_relationships` | Infer entity links with confidence scores | Extracted data |
| `populate_graph` | MERGE nodes + relationships into Neo4j | Running Neo4j |
| `generate_embeddings` | Vector embeddings via GenAI plugin | OPENAI_API_KEY + Neo4j |
| `validate` | Node counts, orphans, traversals | Running Neo4j |

## Validation Checkpoints

| Checkpoint | Review | Threshold |
|-----------|--------|-----------|
| After `extract_recommendations` | 10 random samples | >95% accuracy |
| After `extract_key_questions` | All 12 reviewed | 100% accuracy |
| After `resolve_pmids` | PMID resolution rate | >90% resolved |
| After `build_relationships` | Low-confidence links | <10 flagged |
| After `validate` | Graph in Neo4j Browser | All traversals work |

## Troubleshooting

### "Config file not found"
Provide the full path: `--config configs/guidelines/diabetes-t2-2023.yaml`

### "PDF not found"
Place PDF at `docs/source-guidelines/VADOD-Diabetes-CPG_Final_508.pdf`

### "API key not found"
Set `ANTHROPIC_API_KEY` in `.env` file at project root.

### "Neo4j connection refused"
Start Neo4j: `docker-compose up -d`

### Resuming after failure
Use `--start-from <stage>` to resume from the failed stage.

### LLM extraction errors
Check `data/guidelines/<slug>/checkpoints/` for saved progress. The batch processor resumes automatically.
