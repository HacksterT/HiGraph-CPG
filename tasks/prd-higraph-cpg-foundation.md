# PRD: HiGraph-CPG Foundation - Graph Database Infrastructure

## Overview

**Feature**: Core Neo4j graph database infrastructure for clinical practice guideline knowledge representation

**Description**: Establish the foundational graph database architecture that will store and enable querying of clinical practice guideline knowledge. This includes Neo4j Docker environment setup, core schema definition with 17 entity types, relationship modeling, and vector search capability for semantic queries.

**Problem**: Clinical practice guidelines exist as static documents that are difficult to query, update, and integrate with AI-powered decision support tools. We need a dynamic, queryable knowledge graph infrastructure as the foundation.

**Context**: This is the first phase of HiGraph-CPG, focusing exclusively on infrastructure and schema. Subsequent PRDs will handle data ingestion, API development, and chatbot integration.

---

## Working Backlog

### Phase 1: Infrastructure & Core Schema

- [x] **STORY-01**: As a guideline author, I want a Neo4j graph database running locally in Docker so that I can begin structuring clinical knowledge
  - **Priority**: Must-Have
  - **Acceptance Criteria**: (verified at Manual Testing checkpoint)
    - [x] Neo4j Community Edition running in Docker container on localhost:7474 (confirmed no conflict in `C:\Projects\PORTS.md`, updated with assigned ports)
    - [x] Neo4j Browser accessible with credentials (neo4j/Troyster1)
    - [x] Docker Compose file allows easy start/stop of database
    - [x] Data persists across container restarts via volume mounting
    - [x] Environment variables configured for database credentials
  - **Tasks**:
    - [x] Backend: Create docker-compose.yml with Neo4j Community Edition 2025.12.1
    - [x] Backend: Configure volume mount for data persistence at ./neo4j/data
    - [x] Backend: Configure volume mount for logs at ./neo4j/logs
    - [x] Backend: Set environment variables (NEO4J_AUTH, memory limits)
    - [x] Backend: Create .env.example with required environment variables
    - [x] Backend: Add neo4j/ directory to .gitignore
    - [x] Local Testing: Start container, verify Neo4j Browser access, restart container and verify data persistence
    - [x] Manual Testing: CHECKPOINT — User verified Neo4j Browser works at localhost:7474
    - [N/A] Git: Not a git repo — skipped
  - **Implementation Notes**: Neo4j 2025.12.1 Community Edition pulled via `neo4j:community` tag. GenAI and APOC plugins auto-installed via `NEO4J_PLUGINS=["genai","apoc"]`. Ports 7474 (HTTP) and 7687 (Bolt) registered in `C:\Projects\PORTS.md`. Docker setup instructions documented in `CLAUDE.md` (commands section).
  - **Blockers**: None

- [x] **STORY-02**: As a guideline author, I want the complete graph schema defined with all entity types and relationships so that clinical knowledge can be consistently structured
  - **Priority**: Must-Have
  - **Acceptance Criteria**: (verified at Manual Testing checkpoint)
    - [x] All 17 primary node types (Guideline, ClinicalModule, KeyQuestion, EvidenceBody, Study, Recommendation, ClinicalScenario, Intervention, Outcome, OutcomeMeasurement, Benefit, AdverseEvent, PatientPopulation, PatientCharacteristic, Contraindication, QualityAssessment, DecisionFramework) defined with constraints
    - [x] All relationship types defined with clear directionality
    - [x] Unique constraints on primary identifiers (e.g., rec_id, study_id, pmid)
    - [x] Required properties enforced at application layer (IS NOT NULL constraints are Enterprise-only)
    - [x] Schema can be queried and visualized in Neo4j Browser
  - **Tasks**:
    - [x] Backend: Create schema/constraints.cypher with CREATE CONSTRAINT statements for all node types
    - [x] Backend: Create schema/indexes.cypher with CREATE INDEX statements for frequently queried properties
    - [x] Backend: Create schema/node_types.json documenting all 17 node types with properties and descriptions
    - [x] Backend: Create schema/relationship_types.json documenting all relationship types with descriptions
    - [x] Backend: Create Python script scripts/init_schema.py to execute Cypher files against Neo4j
    - [x] Backend: Add neo4j Python driver to requirements.txt
    - [x] Documentation: docs/technical/SCHEMA.md contains complete schema documentation (pre-existing)
    - [x] Local Testing: Run init_schema.py — 31/31 statements succeeded (17 uniqueness constraints, 11 indexes, 3 vector indexes)
    - [x] Manual Testing: CHECKPOINT — User verified constraints in Neo4j Browser
    - [N/A] Git: Not a git repo — skipped
  - **Implementation Notes**: Property existence (IS NOT NULL) constraints require Neo4j Enterprise Edition and are not available in Community. Required properties are enforced at the application layer (Python scripts) instead. This is documented in `schema/constraints.cypher`.
  - **Blockers**: ~~STORY-01 must be complete~~ Done

- [x] **STORY-03**: As a clinician, I want vector search capability configured so that I can perform semantic similarity searches on clinical concepts
  - **Priority**: Must-Have
  - **Acceptance Criteria**: (verified at Manual Testing checkpoint)
    - [x] Vector index created on node text properties (recommendation text, intervention descriptions, clinical scenario descriptions)
    - [x] Test embeddings can be generated and stored (4 test nodes, 1536 dimensions each)
    - [x] Vector similarity search returns semantically related nodes (ANN search verified)
    - [x] Index supports at least 1536-dimension embeddings (OpenAI embedding size)
    - [x] Pairwise cosine similarity verified via native `vector.similarity.cosine()`
  - **Tasks**:
    - [x] Backend: Create schema/vector_indexes.cypher with CREATE VECTOR INDEX statements
    - [x] Backend: GenAI plugin enabled via docker-compose.yml `NEO4J_PLUGINS=["genai","apoc"]`
    - [x] Backend: Create scripts/test_vector_search.py with sample embedding generation
    - [x] Backend: Embeddings generated server-side via Neo4j GenAI plugin — no Python embedding library needed
    - [x] Backend: Create utility function in utils/embeddings.py for consistent embedding generation
    - [x] Backend: Add sample vector search queries to test script (ANN + pairwise cosine)
    - [x] Documentation: Embedding approach documented in docs/technical/EMBEDDING_STRATEGY.md (covers vector search setup, data flow, Cypher patterns, and cost estimation)
    - [x] Local Testing: Generated embeddings for test data, performed similarity search, verified results
    - [x] Manual Testing: CHECKPOINT — User verified vector search returns semantically similar results
    - [N/A] Git: Not a git repo — skipped
  - **Implementation Notes**: Neo4j 2025.12.1 GenAI plugin uses `genai.vector.encodeBatch()` (not `ai.text.embed()` which is a planned future API). Config map requires `token` key (not `apiKey`). Default model is `text-embedding-ada-002`; we override to `text-embedding-3-small`. See `docs/technical/EMBEDDING_STRATEGY.md` for full rationale, data flow diagram, and procedure name evolution history.
  - **Blockers**: ~~STORY-02 must be complete~~ Done

- [x] **STORY-04**: As a guideline author, I want example graph traversal patterns documented and tested so that I understand how to query clinical knowledge
  - **Priority**: Should-Have
  - **Acceptance Criteria**: (verified at Manual Testing checkpoint)
    - [x] 7 example traversal patterns documented with Cypher queries (exceeded 5 minimum)
    - [x] Examples cover: evidence chain (Study→EvidenceBody→Recommendation), clinical decision (Scenario→Recommendation), benefit-harm balance, contraindication checking, versioning queries, patient-specific filtering, semantic similarity
    - [x] Each example includes comments explaining the clinical use case
    - [x] Test data created to demonstrate each traversal pattern (all 17 entity types)
    - [x] All example queries execute successfully (7/7 passing)
  - **Tasks**:
    - [x] Backend: Create scripts/seed_test_data.cypher with sample nodes and relationships for each entity type
    - [x] Backend: Create scripts/example_traversals.cypher with 7 documented query patterns
    - [x] Backend: Create Python script scripts/run_traversals.py to execute and verify traversal queries
    - [x] Documentation: docs/technical/GRAPH_TRAVERSALS.md contains detailed traversal examples (pre-existing)
    - [x] Testing: Create tests/test_traversals.py to verify each query pattern works (10 tests, all passing)
    - [x] Local Testing: Seed test data, run all traversal examples, verify outputs match expected patterns
    - [x] Manual Testing: CHECKPOINT — User verified traversal results
    - [N/A] Git: Not a git repo — skipped
  - **Implementation Notes**: `run_traversals.py` auto-cleans existing data before seeding to avoid constraint violations on re-run. Test data uses realistic diabetes CPG examples drawn from SCHEMA.md (not extracted from actual CPG PDF — that is Phase 2).
  - **Blockers**: ~~STORY-02 must be complete~~ Done

---

## Additional Deliverables (produced during Phase 1)

- [x] **`tasks/query-strategy.md`**: Hybrid search and re-ranking architecture for future Phase 3/4 implementation. Covers query analysis, vector retrieval path, graph traversal path, result fusion (RRF), re-ranking strategies (cross-encoder, LLM-based, clinical rule-based), and answer generation pipeline. Developed during Phase 1 to inform infrastructure decisions.

---

## Non-Goals

- **Data ingestion** from diabetes guideline PDF (covered in Phase 2 PRD: `tasks/prd-higraph-cpg-data-ingestion.md`)
- **Query API / hybrid search** (covered in Phase 3; see `tasks/query-strategy.md` for retrieval architecture design)
- **Chatbot integration** (covered in Phase 4; query-strategy.md defines the re-ranking and answer generation pipeline)
- **Authentication/authorization** (future consideration)
- **Production deployment** configuration (focus on local Docker only)
- **UI/web interface** (covered in later PRD)
- **Automated evidence monitoring** (future enhancement)

---

## Dependencies

### Internal

- None (this is the foundational PRD)

### External

- Docker Desktop installed and running
- Python 3.10+ for scripting
- Neo4j Community Edition 2025.11+ (via `neo4j:community` Docker tag)
- OpenAI API key (for embedding generation via GenAI plugin)

---

## Success Metrics

- [x] Neo4j database running locally with <5 second startup time
- [x] All 17 node types and constraints created without errors (31/31 statements)
- [x] Vector index created and queryable (3 vector indexes, ANN search verified)
- [x] All example traversal queries execute in <100ms (7/7 traversals)
- [x] Complete technical documentation for schema and traversals (SCHEMA.md, GRAPH_TRAVERSALS.md, EMBEDDING_STRATEGY.md)
- [x] Zero data loss on container restart

---

## Resolved Questions

1. **Embedding provider**: **Decided — OpenAI `text-embedding-3-small`** via Neo4j GenAI plugin (`genai.vector.encodeBatch()`). Server-side generation, no Python SDK needed. Cost negligible (<$0.01 for full CPG). See `docs/technical/EMBEDDING_STRATEGY.md`.

2. **Memory allocation**: 2GB heap is sufficient for initial development.
   - **Can adjust in docker-compose.yml as needed**

3. **APOC procedures**: **Decided — Yes**, included via `NEO4J_PLUGINS=["genai","apoc"]` in docker-compose.yml.

4. **GDS library**: **Not needed**. Native `vector.similarity.cosine()` handles pairwise similarity. `db.index.vector.queryNodes()` handles ANN search. Both work on Community Edition.

5. **Property existence constraints**: **Community Edition limitation**. IS NOT NULL constraints require Enterprise Edition. Required properties enforced at application layer instead.

---

## Appendix

### Directory Structure (as built)

```
HiGraph-CPG/
├── docker-compose.yml
├── .env.example
├── .env                         # Git-ignored, actual credentials
├── .gitignore
├── requirements.txt
├── CLAUDE.md
├── neo4j/                       # Git-ignored, Docker volumes
│   ├── data/
│   └── logs/
├── schema/
│   ├── constraints.cypher       # 17 uniqueness constraints
│   ├── indexes.cypher           # 7 standard + 4 compound indexes
│   ├── vector_indexes.cypher    # 3 vector indexes (1536-dim, cosine)
│   ├── node_types.json
│   └── relationship_types.json
├── scripts/
│   ├── init_schema.py
│   ├── seed_test_data.cypher
│   ├── example_traversals.cypher
│   ├── run_traversals.py
│   └── test_vector_search.py
├── utils/
│   ├── __init__.py
│   └── embeddings.py
├── tests/
│   ├── __init__.py
│   └── test_traversals.py
├── docs/
│   ├── EXECUTIVE_SUMMARY.md
│   ├── source-guidelines/
│   │   ├── VADOD-Diabetes-CPG_Final_508.pdf
│   │   └── Diabetes-Clinical-Educator-Edition-3Jan2024.pdf
│   └── technical/
│       ├── SCHEMA.md
│       ├── GRAPH_TRAVERSALS.md
│       └── EMBEDDING_STRATEGY.md
└── tasks/
    ├── prd-higraph-cpg-foundation.md
    ├── prd-higraph-cpg-data-ingestion.md
    ├── project-overview.md
    └── query-strategy.md
```

### Neo4j Configuration Reference

- **Port mappings**: 7474 (HTTP), 7687 (Bolt) — registered in `C:\Projects\PORTS.md`
- **Memory**: NEO4J_server_memory_heap_initial__size=2G, NEO4J_server_memory_heap_max__size=2G
- **Page cache**: NEO4J_server_memory_pagecache_size=1G
- **Plugins**: GenAI (embeddings via `genai.vector.encodeBatch()`), APOC Extended (utilities)
- **Security**: Development uses NEO4J_AUTH=neo4j/Troyster1

### Technology Stack

- **Database**: Neo4j Community Edition 2025.12.1 (via `neo4j:community` Docker tag)
- **Container**: Docker Compose
- **Plugins**: GenAI (embeddings), APOC Extended (utilities)
- **Language**: Python 3.10+
- **Driver**: neo4j-driver (Python)
- **Embeddings**: OpenAI `text-embedding-3-small` via Neo4j GenAI plugin (`genai.vector.encodeBatch()`)
- **Similarity**: Native `vector.similarity.cosine()` (no GDS)
- **Testing**: pytest

---

**Document Version**: 2.0
**Created**: February 4, 2026
**Completed**: February 4, 2026
**Status**: Complete
