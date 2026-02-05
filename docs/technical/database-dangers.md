# Database Dangers & Recovery Guide

This document describes the data persistence risks with Neo4j on Windows/Docker and how to prevent and recover from data loss.

## The Problem: WSL2 9p Filesystem Issues

When running Neo4j in Docker on Windows, the database files are accessed through WSL2's 9p filesystem protocol. This can cause **silent data loss** where Neo4j recreates an empty database instead of loading existing data.

### Symptoms

1. Neo4j logs show `"Creating 'DatabaseId{...}'"` instead of `"Starting 'DatabaseId{...}'"`
2. Database is empty after container restart
3. No explicit error messages - failure is silent

### Root Cause

The 9p filesystem protocol used by WSL2 to share files between Windows and Linux containers has limitations with:
- File locking consistency
- Transaction log validation
- Timing/sync during container restarts

When Neo4j starts and cannot validate its transaction logs (due to 9p issues), it may reinitialize the database as a safety measure.

## Prevention: Use Named Volumes

**Never use bind mounts for Neo4j data on Windows.** Instead, use Docker named volumes which are stored in Docker's native storage (inside WSL2) and avoid the 9p protocol entirely.

### Bad (Bind Mounts) - Prone to Data Loss

```yaml
services:
  neo4j:
    volumes:
      - ./neo4j/data:/data      # DANGEROUS on Windows!
      - ./neo4j/logs:/logs
```

### Good (Named Volumes) - Reliable

```yaml
services:
  neo4j:
    volumes:
      - neo4j_data:/data        # Safe - stored in Docker's WSL2 storage
      - neo4j_logs:/logs

volumes:
  neo4j_data:
    name: higraph-cpg-neo4j-data
  neo4j_logs:
    name: higraph-cpg-neo4j-logs
```

## Safe Docker Operations

### Starting/Stopping Containers

```bash
# Safe - graceful shutdown
docker-compose down

# Safe - start containers
docker-compose up -d
```

### Dangerous Commands (Use with Caution)

```bash
# DANGER: Removes all data volumes!
docker-compose down -v

# DANGER: Removes all unused volumes system-wide!
docker volume prune

# DANGER: Removes specific volume and all data!
docker volume rm higraph-cpg-neo4j-data
```

### Checking Volume Status

```bash
# List all volumes
docker volume ls | grep higraph

# Inspect a volume (shows creation time, mount point)
docker volume inspect higraph-cpg-neo4j-data
```

## Recovery Procedure

If the database is empty (0 nodes), follow these steps to repopulate from extracted JSON files:

### Prerequisites

- Extracted JSON files exist in `data/guidelines/diabetes-t2-2023/extracted/`
- Neo4j container is running and healthy
- Virtual environment is activated

### Step 1: Initialize Schema

```bash
.venv\Scripts\python.exe scripts/init_schema.py
```

This creates constraints and indexes. Wait for vector indexes to show `state=ONLINE`.

### Step 2: Populate Nodes (in order)

```bash
# Must run in this order - later scripts depend on earlier nodes
.venv\Scripts\python.exe scripts/graph_population/populate_guideline.py --config configs/guidelines/diabetes-t2-2023.yaml
.venv\Scripts\python.exe scripts/graph_population/populate_clinical_modules.py --config configs/guidelines/diabetes-t2-2023.yaml
.venv\Scripts\python.exe scripts/graph_population/populate_recommendations.py --config configs/guidelines/diabetes-t2-2023.yaml
.venv\Scripts\python.exe scripts/graph_population/populate_key_questions.py --config configs/guidelines/diabetes-t2-2023.yaml
.venv\Scripts\python.exe scripts/graph_population/populate_evidence_bodies.py --config configs/guidelines/diabetes-t2-2023.yaml
.venv\Scripts\python.exe scripts/graph_population/populate_studies.py --config configs/guidelines/diabetes-t2-2023.yaml
```

### Step 3: Populate Relationships

```bash
.venv\Scripts\python.exe scripts/graph_population/populate_relationships.py --config configs/guidelines/diabetes-t2-2023.yaml
```

### Step 4: Generate Embeddings

```bash
# Costs ~$0.01 via OpenAI API
.venv\Scripts\python.exe scripts/graph_population/generate_embeddings.py --config configs/guidelines/diabetes-t2-2023.yaml
```

### Step 5: Validate

```bash
.venv\Scripts\python.exe scripts/graph_population/validate_graph.py --config configs/guidelines/diabetes-t2-2023.yaml
```

### Step 6: Run Tests

```bash
.venv\Scripts\pytest.exe tests/test_api_search.py -v
```

## Expected Database State

After successful population:

| Entity | Count |
|--------|-------|
| Guideline | 1 |
| ClinicalModule | 9 |
| Recommendation | 26 |
| KeyQuestion | 12 |
| EvidenceBody | 12 |
| Study | 154 |
| **Total Nodes** | **214** |
| **Total Relationships** | **221** |
| **Embedded Nodes** | **190** |

## Backup Strategy

### Your Data is Safe in JSON Files

The extracted JSON files in `data/guidelines/diabetes-t2-2023/extracted/` are your authoritative data source:

- `guideline.json` - Guideline metadata
- `clinical_modules.json` - 9 clinical modules
- `recommendations.json` - 26 recommendations
- `key_questions.json` - 12 key questions
- `evidence_bodies.json` - 12 evidence bodies
- `studies.json` - 154 studies (includes PubMed abstracts, PMIDs, MeSH terms)
- `relationships.json` - Relationship definitions

These files are version-controlled in git. The Neo4j database can always be repopulated from them.

### What's NOT Backed Up

- **Embeddings** - Must be regenerated (~$0.01 cost)
- **Neo4j indexes** - Recreated by `init_schema.py`

## Incident History

### 2026-02-05: Multiple Data Loss Events

**Timeline:**
| Time (UTC) | Event |
|------------|-------|
| Feb 4, 21:23 | Initial database creation |
| Feb 5, 12:38 | Database recreated (data loss #1) |
| Feb 5, 16:12 | Database recreated (data loss #2) |
| Feb 5, 16:16 | Database recreated (data loss #3) |

**Root Cause:** Bind mounts + WSL2 9p filesystem issues

**Resolution:**
1. Migrated to named volumes
2. Repopulated from JSON files
3. Regenerated embeddings
4. All 38 API tests passing

**Prevention:** Updated `docker-compose.yml` to use named volumes instead of bind mounts.

## Quick Reference

### Check Database Status

```bash
# Via API
curl http://localhost:8100/health

# Via Cypher
.venv\Scripts\python.exe -c "
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
load_dotenv()
driver = GraphDatabase.driver(os.getenv('NEO4J_URI'), auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD')))
with driver.session() as session:
    result = session.run('MATCH (n) RETURN count(n) as nodes')
    print(f'Nodes: {result.single()[\"nodes\"]}')
driver.close()
"
```

### Full Repopulation Script

For convenience, here's a single command to repopulate everything:

```bash
cd C:\Projects\va-work\HiGraph-CPG

# Run all population scripts in sequence
.venv\Scripts\python.exe scripts/init_schema.py && \
.venv\Scripts\python.exe scripts/graph_population/populate_guideline.py --config configs/guidelines/diabetes-t2-2023.yaml && \
.venv\Scripts\python.exe scripts/graph_population/populate_clinical_modules.py --config configs/guidelines/diabetes-t2-2023.yaml && \
.venv\Scripts\python.exe scripts/graph_population/populate_recommendations.py --config configs/guidelines/diabetes-t2-2023.yaml && \
.venv\Scripts\python.exe scripts/graph_population/populate_key_questions.py --config configs/guidelines/diabetes-t2-2023.yaml && \
.venv\Scripts\python.exe scripts/graph_population/populate_evidence_bodies.py --config configs/guidelines/diabetes-t2-2023.yaml && \
.venv\Scripts\python.exe scripts/graph_population/populate_studies.py --config configs/guidelines/diabetes-t2-2023.yaml && \
.venv\Scripts\python.exe scripts/graph_population/populate_relationships.py --config configs/guidelines/diabetes-t2-2023.yaml && \
.venv\Scripts\python.exe scripts/graph_population/generate_embeddings.py --config configs/guidelines/diabetes-t2-2023.yaml && \
.venv\Scripts\python.exe scripts/graph_population/validate_graph.py --config configs/guidelines/diabetes-t2-2023.yaml
```

## See Also

- [SCHEMA.md](./SCHEMA.md) - Neo4j schema definition
- [EMBEDDING_STRATEGY.md](./EMBEDDING_STRATEGY.md) - Embedding approach
- [GRAPH_TRAVERSALS.md](./GRAPH_TRAVERSALS.md) - Cypher query patterns
