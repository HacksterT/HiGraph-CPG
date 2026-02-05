# HiGraph-CPG Backup Strategy

## Overview

This document describes the backup and recovery procedures for the HiGraph-CPG Neo4j database. The database uses Docker named volumes for persistence, which provides better reliability than bind mounts but still requires explicit backup procedures.

## Why Backups Matter

**Past data loss incident (2026-02-05):** The database was cleared due to WSL2 9p filesystem issues with Docker bind mounts. This led to migration to named volumes and implementation of explicit backup procedures.

## Backup Tools

### 1. Quick Backup (JSON Export)

**Script:** `scripts/backup_database.py`

```bash
# Create timestamped backup
.venv/Scripts/python.exe scripts/backup_database.py

# Create named backup
.venv/Scripts/python.exe scripts/backup_database.py --output-dir backups/pre-migration
```

**What it backs up:**
- All nodes (excluding embeddings)
- All relationships with properties
- Backup summary with counts

**What it doesn't backup:**
- Embeddings (regenerate for ~$0.01)
- Schema/indexes (use init_schema_v2.py)

### 2. Restore from Backup

**Script:** `scripts/restore_database.py`

```bash
# Restore (additive - merges with existing data)
.venv/Scripts/python.exe scripts/restore_database.py --input-dir backups/2026-02-05-verified

# Restore with clear (replaces all data)
.venv/Scripts/python.exe scripts/restore_database.py --input-dir backups/2026-02-05-verified --clear-first

# Then regenerate embeddings
.venv/Scripts/python.exe scripts/graph_population/generate_embeddings.py --config configs/guidelines/diabetes-t2-2023.yaml
```

## Docker Volume Management

### Named Volumes (Current Setup)

The database uses Docker named volumes for data persistence:
- `higraph-cpg-neo4j-data` - Database files
- `higraph-cpg-neo4j-logs` - Log files

### DANGER: Volume Deletion

**NEVER run `docker-compose down -v`** - This deletes all volumes and all data!

Safe commands:
```bash
docker-compose down      # Stops containers, keeps volumes
docker-compose restart   # Restarts containers, keeps data
docker-compose up -d     # Starts containers
```

Dangerous commands:
```bash
docker-compose down -v   # DELETES ALL DATA
docker volume rm ...     # DELETES SPECIFIED VOLUME
docker system prune -a --volumes  # DELETES ALL VOLUMES
```

### Volume Backup (Full Database)

For complete database backup including transaction logs:

```bash
# Stop Neo4j
docker-compose stop neo4j

# Create volume backup
docker run --rm -v higraph-cpg-neo4j-data:/data -v $(pwd)/backups:/backup alpine tar czf /backup/neo4j-data-$(date +%Y%m%d).tar.gz -C /data .

# Restart Neo4j
docker-compose start neo4j
```

## Backup Schedule Recommendations

| Event | Action |
|-------|--------|
| Before any Docker operations | Run backup_database.py |
| Before schema changes | Run backup_database.py |
| After data population | Run backup_database.py |
| Weekly | Full volume backup |
| Before migrations | Both JSON and volume backup |

## Recovery Scenarios

### Scenario 1: Accidental Data Deletion

```bash
# Restore from JSON backup
.venv/Scripts/python.exe scripts/restore_database.py --input-dir backups/latest --clear-first

# Regenerate embeddings
.venv/Scripts/python.exe scripts/graph_population/generate_embeddings.py --config configs/guidelines/diabetes-t2-2023.yaml
```

### Scenario 2: Volume Deleted

```bash
# Recreate volumes and start Neo4j
docker-compose up -d

# Wait for Neo4j to be healthy
# Initialize schema
.venv/Scripts/python.exe scripts/init_schema_v2.py

# Restore data
.venv/Scripts/python.exe scripts/restore_database.py --input-dir backups/latest

# Regenerate embeddings
.venv/Scripts/python.exe scripts/graph_population/generate_embeddings.py --config configs/guidelines/diabetes-t2-2023.yaml
```

### Scenario 3: Complete Repopulation from Source

If no backup exists, repopulate from extracted JSON files:

```bash
# Run all population scripts in order
.venv/Scripts/python.exe scripts/graph_population/populate_guideline.py --config configs/guidelines/diabetes-t2-2023.yaml
.venv/Scripts/python.exe scripts/graph_population/populate_clinical_modules.py --config configs/guidelines/diabetes-t2-2023.yaml
.venv/Scripts/python.exe scripts/graph_population/populate_recommendations.py --config configs/guidelines/diabetes-t2-2023.yaml
.venv/Scripts/python.exe scripts/graph_population/populate_key_questions.py --config configs/guidelines/diabetes-t2-2023.yaml
.venv/Scripts/python.exe scripts/graph_population/populate_evidence_bodies.py --config configs/guidelines/diabetes-t2-2023.yaml
.venv/Scripts/python.exe scripts/graph_population/populate_studies.py --config configs/guidelines/diabetes-t2-2023.yaml
.venv/Scripts/python.exe scripts/graph_population/populate_relationships.py --config configs/guidelines/diabetes-t2-2023.yaml
.venv/Scripts/python.exe scripts/graph_population/generate_embeddings.py --config configs/guidelines/diabetes-t2-2023.yaml
.venv/Scripts/python.exe scripts/graph_population/validate_graph.py --config configs/guidelines/diabetes-t2-2023.yaml
```

## Current Backup Location

Backups are stored in the `backups/` directory (gitignored for size):
- `backups/2026-02-05-verified/` - Current verified backup

## Verification Commands

Check database state anytime:

```bash
.venv/Scripts/python.exe -c "
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
load_dotenv()
driver = GraphDatabase.driver(os.getenv('NEO4J_URI'), auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD')))
with driver.session() as s:
    r = s.run('MATCH (n) RETURN count(n) as nodes')
    print(f'Nodes: {r.single()[\"nodes\"]}')
    r = s.run('MATCH ()-[r]->() RETURN count(r) as rels')
    print(f'Relationships: {r.single()[\"rels\"]}')
driver.close()
"
```

Expected values (as of 2026-02-05):
- Nodes: 214
- Relationships: 221
- Embedded nodes: 190
