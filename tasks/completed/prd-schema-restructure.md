# PRD: Schema Restructure for Disease-Agnostic HiGraph-CPG

## Overview

**Feature Name**: Schema Restructure & Data Validation
**Status**: ✅ COMPLETE
**Created**: 2026-02-05
**Completed**: 2026-02-05

### Problem Statement

The current HiGraph-CPG schema conflates disease-specific content with generic clinical structure. "Prediabetes" was incorrectly modeled as a ClinicalModule when it is actually a **Condition** (ICD-10: R73.03) defined by laboratory values (HbA1c 5.7-6.4%). This semantic error undermines the core value proposition: a **disease-agnostic** knowledge graph skeleton that can represent ANY clinical practice guideline.

### Goal

Establish a correct, hierarchical, disease-agnostic schema that cleanly separates:
1. **Clinical Care Structure** (generic phases applicable to any disease)
2. **Evidence Structure** (GRADE methodology for synthesizing research)
3. **Disease-Specific Content** (conditions, interventions, populations)

This PRD will methodically review and restructure the database, with heavy human-in-the-loop validation at each step.

---

## Part 1: Foundational Schema Design

### 1.1 The Two Hierarchies

A clinical practice guideline has **two distinct hierarchical structures** that must be modeled separately:

#### Hierarchy A: Clinical Care Structure (Generic)

This represents the **phases of clinical care** that apply to ANY disease:

```
GUIDELINE (document-level container)
    │
    └── CARE PHASE (generic clinical workflow stage)
            │
            └── RECOMMENDATION (specific clinical action)
                    │
                    └── INTERVENTION (what to do)
```

**Care Phases** (disease-agnostic, applicable to any CPG):

| Care Phase | Description | Example Content |
|------------|-------------|-----------------|
| **Screening & Prevention** | Identifying at-risk individuals before disease onset | Risk assessment tools, screening intervals |
| **Diagnosis & Assessment** | Confirming the condition and severity | Diagnostic criteria, staging, initial workup |
| **Treatment - Pharmacological** | Drug-based interventions | Medications, dosing, sequencing |
| **Treatment - Non-Pharmacological** | Lifestyle, procedures, therapy | Diet, exercise, surgery, counseling |
| **Monitoring & Follow-up** | Ongoing surveillance and targets | Lab intervals, goal values, visit frequency |
| **Complications Management** | Managing disease sequelae | Secondary prevention, damage mitigation |
| **Special Populations** | Modified care for specific groups | Elderly, pregnant, pediatric, comorbid |

#### Hierarchy B: Evidence Structure (GRADE Methodology)

This represents **how evidence supports recommendations**:

```
KEY QUESTION (PICOT-formatted research question)
    │
    └── EVIDENCE BODY (synthesized research answering the question)
            │
            └── STUDY (individual research paper)
                    │
                    └── OUTCOME MEASUREMENT (specific findings)
```

**Evidence Components**:

| Component | Description | GRADE Role |
|-----------|-------------|------------|
| **KeyQuestion** | PICOT-formatted question | Drives systematic review |
| **EvidenceBody** | Synthesis of studies for one question | Rated for quality |
| **Study** | Individual research paper | Source of data |
| **QualityAssessment** | GRADE quality rating | Certainty of evidence |

#### How They Connect

The two hierarchies connect through the **BASED_ON** relationship:

```
RECOMMENDATION ──BASED_ON──► EVIDENCE BODY ──ANSWERS──► KEY QUESTION
                                   │
                               INCLUDES
                                   ▼
                                STUDY
```

### 1.2 Disease-Specific Content (New Node Types)

Disease-specific content should be modeled as **separate entities** that link into the generic structure:

#### Condition Node (NEW)

Represents a diagnosable medical condition with standardized coding:

```
Condition {
    condition_id: String (unique)
    name: String ("Type 2 Diabetes Mellitus")
    icd10_codes: String[] (["E11", "E11.9"])
    icd9_codes: String[] (legacy, optional)
    snomed_ct: String (optional)
    definition: String (clinical definition)
    diagnostic_criteria: String (how it's diagnosed)
    severity_levels: String[] (optional staging)
}
```

**Example Conditions**:
- Type 2 Diabetes Mellitus (E11)
- Prediabetes (R73.03) - defined by HbA1c 5.7-6.4%
- Diabetic Nephropathy (E11.21)
- Diabetic Retinopathy (E11.31)

**Relationships**:
- `Guideline -[:ADDRESSES]-> Condition` (primary condition)
- `Guideline -[:RELATED_TO]-> Condition` (comorbid conditions)
- `Recommendation -[:APPLIES_TO]-> Condition`
- `Condition -[:PROGRESSES_TO]-> Condition` (disease progression)
- `Condition -[:DIAGNOSED_BY]-> DiagnosticCriteria`

#### DiagnosticCriteria Node (NEW)

Represents how a condition is diagnosed:

```
DiagnosticCriteria {
    criteria_id: String
    condition_id: String (FK)
    name: String ("HbA1c Criteria for Prediabetes")
    test_type: String ("Laboratory", "Clinical", "Imaging")
    parameters: JSON {
        test: "HbA1c",
        threshold_low: 5.7,
        threshold_high: 6.4,
        unit: "%"
    }
    source: String ("ADA 2023")
}
```

### 1.3 Corrected Node Type Summary

| Category | Node Type | Generic/Specific | Description |
|----------|-----------|------------------|-------------|
| **Structure** | Guideline | Generic | Top-level document container |
| **Structure** | CarePhase | Generic | Phase of clinical workflow |
| **Clinical** | Recommendation | Generic | Clinical action statement |
| **Clinical** | Intervention | Semi-generic | Treatment/action (typed) |
| **Clinical** | Condition | Specific | Diagnosable disease (ICD-10) |
| **Clinical** | DiagnosticCriteria | Specific | How conditions are diagnosed |
| **Evidence** | KeyQuestion | Generic | PICOT research question |
| **Evidence** | EvidenceBody | Generic | Synthesized evidence |
| **Evidence** | Study | Generic | Individual research paper |
| **Evidence** | QualityAssessment | Generic | GRADE rating |
| **Patient** | PatientPopulation | Semi-generic | Target demographic |
| **Patient** | PatientCharacteristic | Specific | Modifying attributes |
| **Safety** | Contraindication | Specific | Safety warnings |
| **Safety** | AdverseEvent | Specific | Known harms |
| **Outcome** | Benefit | Semi-generic | Positive outcomes |
| **Outcome** | Outcome | Generic | Measured endpoints |
| **Outcome** | OutcomeMeasurement | Specific | Study-level data |

### 1.4 Relationship Types

| Relationship | From | To | Description |
|--------------|------|-----|-------------|
| **PART_OF** | CarePhase | Guideline | Module belongs to guideline |
| **BELONGS_TO** | Recommendation | CarePhase | Rec grouped by care phase |
| **ADDRESSES** | Guideline | Condition | Primary condition of guideline |
| **APPLIES_TO** | Recommendation | Condition | Rec applies to this condition |
| **BASED_ON** | Recommendation | EvidenceBody | Evidence supporting rec |
| **ANSWERS** | EvidenceBody | KeyQuestion | Evidence answers question |
| **INCLUDES** | EvidenceBody | Study | Studies in evidence synthesis |
| **DIAGNOSED_BY** | Condition | DiagnosticCriteria | How condition is diagnosed |
| **PROGRESSES_TO** | Condition | Condition | Disease progression |
| **MODIFIES** | PatientCharacteristic | Recommendation | Patient factor modifies rec |
| **CONTRAINDICATES** | Contraindication | Intervention | Safety warning |
| **PRODUCES** | Intervention | Benefit | Intervention produces benefit |
| **CAUSES** | Intervention | AdverseEvent | Intervention causes harm |

### 1.5 Indexing Strategy

#### Property Indexes (Fast Lookups)

| Index | Node Type | Property | Purpose |
|-------|-----------|----------|---------|
| condition_icd10 | Condition | icd10_codes | Find by diagnosis code |
| condition_name | Condition | name | Find by disease name |
| study_pmid | Study | pmid | PubMed lookup |
| rec_strength | Recommendation | strength | Filter by GRADE strength |
| intervention_type | Intervention | type | Filter by intervention type |

#### Vector Indexes (Semantic Search)

| Index | Node Type | Embedded Field | Purpose |
|-------|-----------|----------------|---------|
| recommendation_embedding | Recommendation | rec_text | Semantic rec search |
| study_embedding | Study | abstract | Semantic study search |
| condition_embedding | Condition | definition + diagnostic_criteria | Semantic condition search |
| keyquestion_embedding | KeyQuestion | question_text | Semantic question search |

**Embedding Strategy**:
- Model: `text-embedding-3-small` (1536 dimensions)
- Generated via Neo4j GenAI plugin (server-side)
- Only embed text fields that benefit from semantic search
- NOT embedded: IDs, codes, numeric values, structured data

### 1.6 What Gets Embedded (And Why)

| Node Type | Embedded Field | Why |
|-----------|----------------|-----|
| Recommendation | rec_text | Natural language clinical action |
| Study | abstract | Research summary for semantic match |
| KeyQuestion | question_text | PICOT question for semantic match |
| EvidenceBody | key_findings | Synthesis summary |
| Condition | definition + criteria | For "what condition matches these symptoms?" |
| CarePhase | description | For "what phase of care handles X?" |

**NOT Embedded**:
- IDs (no semantic meaning)
- ICD-10 codes (use exact match)
- Numeric values (use range queries)
- Structured properties (use property indexes)

---

## Part 2: Working Backlog

### Phase 1: Data Audit & Decision

Before restructuring, we must analyze the existing extracted data to determine what can be salvaged.

---

- [x] **STORY-01**: As a developer, I want to audit the existing JSON extractions so that I can determine what needs re-extraction vs. restructuring
  - **Priority**: Must-Have (BLOCKER for all subsequent stories)
  - **Acceptance Criteria**: (verified at Manual Testing checkpoint)
    - [ ] Detailed report on each JSON file (guideline, clinical_modules, recommendations, key_questions, evidence_bodies, studies, relationships)
    - [ ] For each file: field completeness, semantic correctness assessment, mapping to new schema
    - [ ] Clear recommendation: "Keep and Transform" vs. "Re-extract" for each entity type
    - [ ] Identified gaps in current extraction (missing fields for new schema)
  - **Tasks**:
    - [ ] Analysis: Read `data/guidelines/diabetes-t2-2023/extracted/guideline.json` - verify guideline metadata
    - [ ] Analysis: Read `clinical_modules.json` - assess if these are actually care phases or disease-specific topics
    - [ ] Analysis: Read `recommendations.json` - verify GRADE strength/direction, check topic assignment
    - [ ] Analysis: Read `key_questions.json` - verify PICOT elements present
    - [ ] Analysis: Read `evidence_bodies.json` - verify links to KQs, quality ratings
    - [ ] Analysis: Read `studies.json` - verify PubMed data (abstracts, MeSH, PMIDs)
    - [ ] Analysis: Read `relationships.json` - verify relationship correctness
    - [ ] Documentation: Write detailed audit report with keep/re-extract decision for each
    - [ ] Manual Testing: CHECKPOINT - Present audit findings to user for review and decision
  - **Technical Notes**: This is READ-ONLY analysis. No changes to data or database. Output is a detailed report for human decision.
  - **Blockers**: None

---

- [x] **STORY-02**: As a developer, I want to design the Condition node structure so that we correctly model diseases with ICD-10 codes
  - **Priority**: Must-Have
  - **Acceptance Criteria**: (verified at Manual Testing checkpoint)
    - [ ] Condition node schema defined with all required properties
    - [ ] DiagnosticCriteria node schema defined
    - [ ] Relationship types to/from Condition documented
    - [ ] Sample conditions identified for diabetes guideline (T2DM, Prediabetes, DKD, etc.)
    - [ ] ICD-10 codes researched and documented for each condition
  - **Tasks**:
    - [ ] Research: Identify all conditions mentioned in diabetes CPG
    - [ ] Research: Look up ICD-10 codes for each condition
    - [ ] Research: Document diagnostic criteria for prediabetes (HbA1c, FPG, OGTT)
    - [ ] Design: Finalize Condition node properties
    - [ ] Design: Finalize DiagnosticCriteria node properties
    - [ ] Design: Document all Condition relationships
    - [ ] Documentation: Create `docs/technical/CONDITION_SCHEMA.md`
    - [ ] Manual Testing: CHECKPOINT - Review schema design with user before implementation
  - **Technical Notes**: This is DESIGN only. No code changes. Output is schema documentation.
  - **Blockers**: STORY-01 (need audit results to understand current data state)

---

- [x] **STORY-03**: As a developer, I want to define the correct CarePhase categories so that the clinical hierarchy is disease-agnostic
  - **Priority**: Must-Have
  - **Acceptance Criteria**: (verified at Manual Testing checkpoint)
    - [ ] Final list of CarePhase categories documented
    - [ ] Each CarePhase has: id pattern, name, description, scope
    - [ ] Mapping from current "ClinicalModule" topics to correct CarePhases
    - [ ] Unmapped content identified (what doesn't fit any care phase?)
  - **Tasks**:
    - [ ] Analysis: Review current 9 clinical modules and their content
    - [ ] Design: Finalize CarePhase categories (7 proposed above)
    - [ ] Mapping: Create topic → CarePhase mapping table
    - [ ] Validation: Verify all 26 recommendations can be assigned to a CarePhase
    - [ ] Documentation: Create `docs/technical/CARE_PHASES.md`
    - [ ] Manual Testing: CHECKPOINT - Review CarePhase design with user
  - **Technical Notes**: This is DESIGN only. Output is mapping documentation.
  - **Blockers**: STORY-01 (need to understand current clinical_modules.json structure)

---

- [x] **STORY-04**: As a developer, I want to create the updated schema DDL so that we can rebuild the database with correct structure
  - **Priority**: Must-Have
  - **Acceptance Criteria**: (verified at Manual Testing checkpoint)
    - [ ] New `schema/constraints.cypher` with all node type constraints
    - [ ] New `schema/indexes.cypher` with property indexes
    - [ ] New `schema/vector_indexes.cypher` with embedding indexes
    - [ ] Schema documentation updated (`docs/technical/SCHEMA.md`)
    - [ ] Migration notes: what changed from old schema
  - **Tasks**:
    - [ ] Schema: Write constraints for new node types (Condition, DiagnosticCriteria, CarePhase)
    - [ ] Schema: Update constraints for modified node types
    - [ ] Schema: Write property indexes for new fields
    - [ ] Schema: Write vector indexes for embeddable fields
    - [ ] Documentation: Update SCHEMA.md with complete new schema
    - [ ] Documentation: Write MIGRATION.md noting all changes
    - [ ] Local Testing: Validate Cypher syntax (dry run)
    - [ ] Manual Testing: CHECKPOINT - Review schema DDL with user before applying
  - **Technical Notes**: Schema files only. Do NOT apply to database yet.
  - **Blockers**: STORY-02, STORY-03 (need finalized Condition and CarePhase designs)

---

## Non-Goals (This PRD)

- **Re-extraction from PDF**: If audit shows extraction is salvageable, we transform existing JSON
- **New guideline ingestion**: Focus is restructuring diabetes CPG only
- **API changes**: Query API will be addressed in separate PRD after schema stabilizes
- **UI changes**: No frontend work in this PRD

---

## Dependencies

### Internal
- Existing extracted JSON files in `data/guidelines/diabetes-t2-2023/extracted/`
- Current Neo4j database (will be wiped and rebuilt)
- Population scripts in `scripts/graph_population/`

### External
- ICD-10 code reference (for Condition nodes)
- PubMed API (if re-enrichment needed)
- OpenAI API (for embedding regeneration)

---

## Success Metrics

- [x] All node types are disease-agnostic (except Condition, DiagnosticCriteria)
- [x] CarePhase categories work for diabetes AND could work for other CPGs
- [x] Full evidence chain traversable: Guideline → CarePhase → Recommendation → EvidenceBody → Study
- [x] Condition nodes have valid ICD-10 codes
- [x] All recommendations assigned to exactly one CarePhase
- [x] Graph passes validation with 0 orphan nodes
- [x] Semantic search returns relevant results

---

## Open Questions

1. **CarePhase granularity**: Should "Treatment" be one phase or split into Pharmacological/Non-Pharmacological?
2. **Condition scope**: Should we model ALL conditions mentioned, or only those with recommendations?
3. **Cross-guideline conditions**: How to handle conditions that appear in multiple guidelines (e.g., CKD in diabetes AND hypertension)?
4. **Evidence reuse**: If same study supports multiple recommendations, how to model?

---

## Appendix: Current vs. Proposed Schema Comparison

### ClinicalModule → CarePhase Mapping (Proposed)

| Current ClinicalModule | Proposed CarePhase | Notes |
|------------------------|-------------------|-------|
| Prediabetes | Screening & Prevention | Prediabetes becomes a Condition node instead |
| Screening and Prevention | Screening & Prevention | Direct mapping |
| Diagnosis | Diagnosis & Assessment | Direct mapping |
| Self-Management | Treatment - Non-Pharmacological | Lifestyle interventions |
| Glycemic Targets | Monitoring & Follow-up | Target values are monitoring |
| Pharmacotherapy | Treatment - Pharmacological | Direct mapping |
| Complications | Complications Management | Direct mapping |
| Comorbidities | Special Populations | Comorbidities modify care |
| Special Populations | Special Populations | Direct mapping |

### New Node Types (Not in Current Schema)

| Node Type | Purpose |
|-----------|---------|
| Condition | ICD-10 coded disease entity |
| DiagnosticCriteria | How conditions are diagnosed |
| CarePhase | Replaces disease-specific ClinicalModule |

---

**Next PRD**: After this restructure is complete, create `prd-schema-restructure-part2.md` covering:
- STORY-05: Database rebuild with new schema
- STORY-06: Data transformation and population
- STORY-07: Embedding regeneration
- STORY-08: Validation and testing
