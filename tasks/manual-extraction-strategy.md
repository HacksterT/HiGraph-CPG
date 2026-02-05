# Manual Extraction Strategy for CPG Knowledge Graphs

## Overview

This document describes the **manual extraction approach** used to bootstrap the VA/DoD Type 2 Diabetes CPG knowledge graph. Unlike the automated pipeline approach (which uses LLM API calls for extraction), this method uses Claude directly reading the PDF and creating structured JSON files.

**When to use this approach:**
- One-time data population (bootstrapping)
- When LLM API costs/tokens are a concern
- When you need tight control over extraction quality
- For smaller documents where human-in-the-loop review is feasible

**When to use the pipeline approach instead:**
- Processing multiple guidelines
- Need for repeatability and automation
- Larger documents where manual review isn't practical

---

## Source Document

- **Document**: VA/DoD Clinical Practice Guideline for the Management of Type 2 Diabetes Mellitus
- **Publication Date**: May 2023
- **Total Pages**: 165
- **Key Sections**:
  - Table 5 (pages 24-70): Recommendations
  - Table A-2 (pages 90-91): Evidence base summary
  - Appendix A (pages 78-87): Key Question details
  - References (pages 150-165): All citations

---

## Phase 2 Entity Types

We populated 6 entity types for the Phase 2 knowledge graph:

| Entity Type | Count | Source Location |
|-------------|-------|-----------------|
| Guideline | 1 | Document metadata |
| ClinicalModule | 9 | Table of contents / section headers |
| Recommendation | 26 | Table 5 |
| KeyQuestion | 12 | Table A-2 and Appendix A |
| EvidenceBody | 12 | One per Key Question |
| Study | 154 | References section (pages 150-165) |

---

## Extraction Process

### Step 1: Guideline Metadata

**Source**: Title page, publication info

**Process**: Extract basic document metadata manually:
- Title, version, publication date
- Issuing organization (VA/DoD)
- Condition covered (Type 2 Diabetes Mellitus)

**Output**: `guideline.json`

```json
{
  "guideline_id": "CPG_DM_2023",
  "title": "VA/DoD Clinical Practice Guideline for the Management of Type 2 Diabetes Mellitus",
  "version": "5.0",
  "publication_date": "2023-05-01",
  "organization": "VA/DoD"
}
```

### Step 2: Clinical Modules

**Source**: Table of contents, major section headers

**Process**: Identify the main clinical topic areas covered:
- Prediabetes
- Screening and Prevention
- Diagnosis
- Self-Management Education
- Glycemic Control
- Pharmacotherapy
- Complications
- Comorbidities
- Special Populations

**Output**: `clinical_modules.json`

### Step 3: Recommendations

**Source**: Table 5 (Recommendations Summary)

**Process**:
1. Read Table 5 page by page
2. For each recommendation, extract:
   - Recommendation number
   - Full recommendation text
   - Strength (Strong, Weak, Neither)
   - Direction (For, Against, Neither)
   - Topic/Category

**Key Challenge**: Table 5 spans many pages. Use "stair-stepping" - read 3-5 pages at a time to maintain context without overwhelming token limits.

**Output**: `recommendations.json`

### Step 4: Key Questions

**Source**: Table A-2 (Evidence Base for KQs), Appendix A (PICOTS details)

**Process**:
1. From Table A-2, extract each KQ's:
   - Question number
   - Question text
   - Number and types of studies
2. From Appendix A, enrich with PICOTS elements:
   - Population
   - Intervention
   - Comparator
   - Outcomes (critical and important)
   - Timing
   - Setting

**Output**: `key_questions.json`

### Step 5: Evidence Bodies

**Source**: Derived from Key Questions and evidence synthesis sections

**Process**: Create one EvidenceBody per Key Question containing:
- Evidence quality rating (from GRADE tables in Appendix E)
- Number of studies
- Study types
- Key findings summary

**Output**: `evidence_bodies.json`

### Step 6: Studies (References)

**Source**: References section (pages 150-165)

**Process - Stair-Stepping Approach**:

The references section is 16 pages with ~168 citations. Extract in batches:

| Batch | Pages | References |
|-------|-------|------------|
| 1 | 150-152 | 1-35 |
| 2 | 153-155 | 36-64 |
| 3 | 156-158 | 65-97 |
| 4 | 159-162 | 98-138 |
| 5 | 163-165 | 139-168 |

For each reference, extract:
- Reference number
- Title
- Authors
- Journal
- Year
- PMID (if printed in citation)
- DOI (if present)

**Filtering**: Not all references are studies. Filter out:
- Other CPGs and guidelines
- Websites and online resources
- Drug package inserts
- Organizational documents

Keep:
- RCTs, systematic reviews, meta-analyses
- Cohort and observational studies
- Diagnostic accuracy studies

**Output**: `studies.json`

---

## PubMed Enrichment

After extracting studies, we enrich them with PubMed metadata to add abstracts, MeSH terms, and verify citation accuracy.

### Why Use PubMed?

1. **Abstracts**: Most PDF citations don't include abstracts. PubMed provides full abstracts for embedding and search.
2. **MeSH Terms**: Standardized medical subject headings enable better categorization.
3. **Verification**: Confirms PMID accuracy and fills in missing metadata.
4. **DOIs**: Retrieves DOIs for citations that don't include them.

### Process

**Prerequisites**:
- Biopython library (`pip install biopython`)
- Optional: PubMed API key (increases rate limit from 3 to 10 requests/second)

**Step 1: Identify PMIDs**

Many VA/DoD CPG citations include PMIDs directly:
```
"... Diabetes Care. 2020;43(1):123-130. PubMed PMID: 31234567."
```

Extract these during the reference parsing step.

**Step 2: Run PubMed Fetch**

Use the `fetch_metadata.py` script:
```bash
python scripts/pubmed/fetch_metadata.py --config configs/guidelines/diabetes-t2-2023.yaml
```

This script:
1. Reads `studies.json`
2. For each study with a PMID, queries PubMed's E-utilities API
3. Retrieves: abstract, MeSH terms, publication types, DOI, full author list
4. Caches results to `data/shared/pubmed_cache/` to avoid repeat API calls
5. Updates `studies.json` with enriched data

**Rate Limiting**:
- Without API key: 0.4 second delay between requests
- With API key: 0.12 second delay

**Expected Results**:
- ~90% of studies should have abstracts after enrichment
- Some older or non-indexed publications may not have PubMed entries

---

## Relationship Building

After extracting all entities, create relationships between them.

### Relationship Types

| Relationship | From | To | Meaning |
|--------------|------|-----|---------|
| PART_OF | ClinicalModule | Guideline | Module belongs to guideline |
| ANSWERS | EvidenceBody | KeyQuestion | Evidence addresses question |
| BASED_ON | Recommendation | EvidenceBody | Recommendation supported by evidence |
| INCLUDES | EvidenceBody | Study | Evidence body includes study |

### Process

**Step 1: Structural Relationships**

These are straightforward:
- All ClinicalModules → PART_OF → the Guideline
- Each EvidenceBody → ANSWERS → its corresponding KeyQuestion

**Step 2: Recommendation-Evidence Links (BASED_ON)**

Match recommendations to evidence bodies by:
1. Topic alignment (e.g., "physical activity" recommendation → KQ5 evidence)
2. Explicit citations in recommendation text
3. Section placement in the document

Assign confidence scores (0.8-0.95) based on match certainty.

**Step 3: Study-Evidence Links (INCLUDES)**

Map studies to evidence bodies by:
1. Study topic matching KQ topic areas
2. Study type matching expected types for each KQ (from Table A-2)
3. Reference number citations in evidence synthesis sections

**Output**: `relationships.json`

```json
[
  {"type": "INCLUDES", "from_type": "EvidenceBody", "from_id": "CPG_DM_2023_EVB_007",
   "to_type": "Study", "to_id": "CPG_DM_2023_STUDY_085", "confidence": 0.85}
]
```

---

## Graph Population

With all JSON files created, populate Neo4j:

```bash
# Populate nodes
python scripts/graph_population/populate_guideline.py --config configs/guidelines/diabetes-t2-2023.yaml
python scripts/graph_population/populate_clinical_modules.py --config configs/guidelines/diabetes-t2-2023.yaml
python scripts/graph_population/populate_recommendations.py --config configs/guidelines/diabetes-t2-2023.yaml
python scripts/graph_population/populate_key_questions.py --config configs/guidelines/diabetes-t2-2023.yaml
python scripts/graph_population/populate_evidence_bodies.py --config configs/guidelines/diabetes-t2-2023.yaml
python scripts/graph_population/populate_studies.py --config configs/guidelines/diabetes-t2-2023.yaml

# Populate relationships
python scripts/graph_population/populate_relationships.py --config configs/guidelines/diabetes-t2-2023.yaml
```

---

## Validation

### Node Count Verification

```cypher
MATCH (n) RETURN labels(n)[0] as type, count(n) as count ORDER BY count DESC
```

Expected:
- Study: 154
- Recommendation: 26
- KeyQuestion: 12
- EvidenceBody: 12
- ClinicalModule: 9
- Guideline: 1

### Relationship Verification

```cypher
MATCH ()-[r]->() RETURN type(r) as type, count(r) as count ORDER BY count DESC
```

Expected:
- INCLUDES: 154
- BASED_ON: 20
- ANSWERS: 12
- PART_OF: 9

### Evidence Chain Test

Verify the full traversal works:

```cypher
MATCH (r:Recommendation)-[:BASED_ON]->(eb:EvidenceBody)-[:INCLUDES]->(s:Study)
RETURN r.rec_id, eb.evidence_id, count(s) as study_count
ORDER BY study_count DESC
LIMIT 5
```

### Orphan Check

No studies should be unlinked:

```cypher
MATCH (s:Study) WHERE NOT ()-[:INCLUDES]->(s) RETURN count(s)
// Should return 0
```

---

## Key Learnings

### What Worked Well

1. **Stair-stepping through the PDF**: Reading 3-5 pages at a time prevents context overflow while maintaining coherence.

2. **Extracting PMIDs from citations**: Many citations already include PMIDs, reducing the need for fuzzy matching.

3. **PubMed enrichment**: Dramatically improves data quality with abstracts and standardized terms.

4. **Topic-based study mapping**: Mapping studies to evidence bodies by topic area is more reliable than trying to trace individual citation numbers.

### Challenges Encountered

1. **Table extraction from PDFs**: Automated table extraction often mangles headers. Manual reading is more reliable for complex tables.

2. **PMID mismatches**: Some PMIDs in the PDF had OCR errors. PubMed API returns metadata for whatever PMID is queried, so some abstracts may not match expected content.

3. **Reference filtering**: Distinguishing studies from other reference types (guidelines, websites) requires judgment.

### Recommendations for Future Extractions

1. **Start with Table A-2**: This gives you the expected study counts per KQ, which helps validate your extraction.

2. **Use batch checkpoints**: Save progress after each batch in case of interruption.

3. **Verify PMID sample**: Spot-check 5-10 PubMed-enriched entries to ensure abstracts match expected topics.

4. **Document decisions**: Note any judgment calls made during extraction for future reference.

---

## File Checklist

After completing manual extraction, you should have:

```
data/guidelines/{guideline-slug}/extracted/
├── guideline.json           # 1 guideline
├── clinical_modules.json    # 9 modules
├── recommendations.json     # 26 recommendations
├── key_questions.json       # 12 key questions
├── evidence_bodies.json     # 12 evidence bodies
├── studies.json             # 154 studies (with PubMed metadata)
├── relationships.json       # 195 relationships
└── study_evidence_links.json # Study-to-evidence mapping
```

---

## Summary

The manual extraction approach successfully populated the Phase 2 knowledge graph with:
- **214 nodes** across 6 entity types
- **195 relationships** across 4 relationship types
- **131 studies** enriched with PubMed abstracts
- **Full evidence chain** traversable from Recommendation → Study

This approach is ideal for bootstrapping a knowledge graph when you need high-quality data and have a single guideline to process. For processing multiple guidelines at scale, consider investing in the automated pipeline approach.
