# HiGraph-CPG Schema V2

**Status**: ✅ Design Complete - Ready for Implementation
**Created**: 2026-02-05
**Last Updated**: 2026-02-05

This document defines the disease-agnostic hierarchical schema for HiGraph-CPG, designed through iterative human-in-the-loop review.

---

## Schema Summary

### Node Types (8)

| Node | Purpose | Embedded | Full-Text |
|------|---------|----------|-----------|
| Guideline | Document container | No | No |
| CarePhase | Clinical workflow stage | No | ✅ Yes |
| Recommendation | Clinical action | ✅ Yes | ✅ Yes |
| KeyQuestion | PICOT research question | ✅ Yes | No |
| EvidenceBody | Synthesized evidence | ✅ Yes | No |
| Study | Research paper | ✅ Yes | No |
| Intervention | Treatment/action | No | No |
| Condition | Disease entity (ICD-10) | No | ✅ Yes |

### Key Relationships

| Relationship | From → To | Purpose |
|--------------|-----------|---------|
| PART_OF | CarePhase → Guideline | Phase belongs to guideline |
| BELONGS_TO | Recommendation → CarePhase | Primary phase assignment |
| RELEVANT_TO | Recommendation → CarePhase | Secondary phase cross-reference |
| BASED_ON | Recommendation → EvidenceBody | Evidence supporting recommendation |
| ANSWERS | EvidenceBody → KeyQuestion | Evidence answers PICOT question |
| INCLUDES | EvidenceBody → Study | Studies in evidence synthesis |
| RECOMMENDS | Recommendation → Intervention | Recommended treatment |
| APPLIES_TO | Recommendation → Condition | Sub-condition specificity |
| PRIMARILY_ABOUT | Guideline → Condition | Main guideline condition |
| REFERENCES | Guideline → Condition | Related conditions (with role) |
| PRECURSOR_TO | Condition → Condition | Severity staging |
| MAY_DEVELOP | Condition → Condition | Downstream complication |
| ASSOCIATED_WITH | Condition ↔ Condition | Comorbidity |

### Indexes

- **8 Unique Constraints**: One per node type on ID field
- **10 Property Indexes**: Common lookup/filter patterns
- **3 Full-Text Indexes**: Recommendation, CarePhase, Condition
- **4 Vector Indexes**: Recommendation, Study, KeyQuestion, EvidenceBody

---

## Design Principles

1. **Disease-agnostic structure**: The skeleton should work for ANY clinical practice guideline
2. **Hierarchical organization**: Clear parent-child relationships at each level
3. **Semantic richness**: Nodes should provide enough context for AI comprehension
4. **Separation of concerns**: Clinical workflow vs. Evidence structure vs. Disease-specific content

---

## Level 0: Guideline (Document Container)

**Status**: ✅ Approved

### Purpose
The Guideline node is the top-level container that provides semantic context about the document's scope and coverage.

### Node Definition

```cypher
Guideline {
    guideline_id: String (unique)
    title: String
    version: String
    publication_date: Date
    publisher: String

    // Semantic context fields
    scope_description: String  // "Management of Type 2 Diabetes in adults..."
    primary_conditions: String[]  // ["Type 2 Diabetes Mellitus"]
    related_conditions: String[]  // ["Prediabetes", "CKD", "CVD", ...]
    target_population: String  // "Adults with or at risk for T2DM"
    clinical_setting: String  // "Primary care, endocrinology"

    // For AI comprehension
    abstract: String  // Executive summary of the guideline
}
```

### Relationships to Conditions

**Approach**: Hybrid - Rich metadata on Guideline + typed relationships to Condition nodes

| Relationship | Description |
|--------------|-------------|
| `PRIMARILY_ABOUT` | The main condition(s) this guideline addresses |
| `REFERENCES` | Any condition mentioned, with `role` property |

**Role values for REFERENCES**:
- `precursor` - Condition that precedes/leads to primary (e.g., Prediabetes)
- `complication` - Downstream effect of primary condition
- `comorbidity` - Co-occurring condition that affects management
- `adverse_effect` - Condition caused by treatment
- `differential` - Condition to rule out

### Example

```cypher
// Guideline node
(:Guideline {
    guideline_id: "VA_DOD_T2DM_2023",
    title: "VA/DoD Clinical Practice Guideline for Management of Type 2 Diabetes Mellitus",
    scope_description: "Evidence-based recommendations for screening, diagnosis, and management of type 2 diabetes in adults",
    primary_conditions: ["Type 2 Diabetes Mellitus"],
    related_conditions: ["Prediabetes", "Diabetic Nephropathy", "Cardiovascular Disease"],
    target_population: "Adults with or at risk for type 2 diabetes",
    clinical_setting: "Primary care, endocrinology, general medicine"
})

// Relationships to Conditions
(g:Guideline)-[:PRIMARILY_ABOUT]->(c:Condition {name: "Type 2 Diabetes Mellitus"})
(g:Guideline)-[:REFERENCES {role: "precursor"}]->(c:Condition {name: "Prediabetes"})
(g:Guideline)-[:REFERENCES {role: "complication"}]->(c:Condition {name: "Diabetic Nephropathy"})
```

### Design Decision Notes
- Conditions mentioned in different contexts (primary, complication, adverse effect) need relationship context
- Rich metadata on Guideline provides AI with semantic understanding of scope
- Condition nodes are independent entities (reusable across guidelines)

---

## The Two Hierarchies

**Status**: ✅ Approved

A clinical practice guideline has **two distinct hierarchical structures** that must be modeled separately but connected:

### Hierarchy A: Clinical Care Structure (Generic)

Represents the **phases of clinical care** that apply to ANY disease:

```
GUIDELINE (document-level container)
    │
    └── CARE PHASE (generic clinical workflow stage)
            │
            └── RECOMMENDATION (specific clinical action)
                    │
                    └── INTERVENTION (what to do - the "I" in PICOT)
```

### Hierarchy B: Evidence Structure (GRADE/PICOT Methodology)

Represents **how evidence supports recommendations**:

```
KEY QUESTION (PICOT-formatted document element)
    │
    └── EVIDENCE BODY (synthesized research answering the question)
            │
            └── STUDY (individual research paper)
```

### The Bridge Between Hierarchies

The two hierarchies connect through the **BASED_ON** relationship:

```
RECOMMENDATION ──BASED_ON──► EVIDENCE BODY ──ANSWERS──► KEY QUESTION
                                   │
                               INCLUDES
                                   ▼
                                STUDY
```

**Critical Design Decision**: There is **no direct relationship** between Recommendation and Key Question. The indirect path through Evidence Body is semantically correct because:

1. **Key Question** is a PICOT-formatted research question in the *document* (not a user query)
2. **Evidence Body** synthesizes studies that answer that question (with GRADE quality rating)
3. **Recommendation** is informed by the *synthesized evidence*, not the question directly

A recommendation doesn't "answer" a key question—it's **based on** the evidence that was gathered to answer that question. The Evidence Body is the mediating construct.

---

## Level 1: Care Phases (Generic Clinical Workflow)

**Status**: ✅ Approved

### Purpose
Care Phases represent generic stages of clinical workflow that apply to any disease. These are **disease-agnostic categories** that can accommodate any clinical practice guideline.

### Node Definition

```cypher
CarePhase {
    phase_id: String (unique)  // "SCREEN", "DIAG", "INTERV", etc.
    name: String
    description: String  // What this phase covers
    sequence_order: Integer  // Typical order in clinical workflow
}
```

### Relationship to Guideline

```cypher
(cp:CarePhase)-[:PART_OF]->(g:Guideline)
```

### Approved Phases

| Phase | ID | Sequence | Description |
|-------|-----|----------|-------------|
| Screening & Prevention | SCREEN | 1 | Identifying at-risk individuals; risk reduction |
| Diagnosis & Assessment | DIAG | 2 | Confirming the condition; initial workup; staging |
| Interventions | INTERV | 3 | All treatments: pharmacological, procedural, lifestyle, therapy |
| Monitoring & Follow-up | MONITOR | 4 | Ongoing surveillance; target values; visit intervals |
| Complications Management | COMP | 5 | Managing disease sequelae; secondary prevention |
| Special Populations | SPECIAL_POP | 6 | Modified care for specific groups (elderly, pregnant, etc.) |

### Design Decisions

1. **Interventions unified**: Combined "Treatment - Pharmacological" and "Treatment - Non-Pharmacological" into single "Interventions" phase
   - Rationale: The **type** of intervention matters less than **what evidence supports it**
   - Intervention type can be a property on the Intervention node (drug, procedure, lifestyle, device)
   - Aligns with PICOT methodology where "I" = Intervention (any type)

2. **Comparator placement**: Comparator is a property of Key Question (the "C" in PICOT), not a separate Care Phase
   - Key Questions contain PICOT elements: Population, Intervention, Comparator, Outcome, Time/Type
   - Comparator flows through Evidence Body → Recommendation via the BASED_ON relationship

3. **Special Populations as phase**: Kept as a Care Phase (not a cross-cutting modifier)
   - Recommendations for special populations often have different evidence bases
   - Easier to query "all recommendations for elderly patients" when grouped

4. **Referral**: Handled as an Intervention type, not a Care Phase
   - "Refer to endocrinologist" is an intervention within any phase

### Example

```cypher
// Care Phases for any guideline
(:CarePhase {phase_id: "SCREEN", name: "Screening & Prevention", sequence_order: 1})
(:CarePhase {phase_id: "DIAG", name: "Diagnosis & Assessment", sequence_order: 2})
(:CarePhase {phase_id: "INTERV", name: "Interventions", sequence_order: 3})
(:CarePhase {phase_id: "MONITOR", name: "Monitoring & Follow-up", sequence_order: 4})
(:CarePhase {phase_id: "COMP", name: "Complications Management", sequence_order: 5})
(:CarePhase {phase_id: "SPECIAL_POP", name: "Special Populations", sequence_order: 6})

// Connected to guideline
(cp:CarePhase {phase_id: "INTERV"})-[:PART_OF]->(g:Guideline {guideline_id: "VA_DOD_T2DM_2023"})
```

---

## Level 2: Recommendations (Clinical Actions)

**Status**: ✅ Approved

### Purpose
Recommendations are specific clinical action statements that belong to a Care Phase and are supported by Evidence Bodies.

### Node Definition

```cypher
Recommendation {
    rec_id: String (unique)
    rec_number: Integer  // Sequential number from source document
    rec_text: String  // The full recommendation statement
    strength_direction: String  // Combined GRADE: "Strong For", "Weak Against", "Neither"
    category: String  // Version status: "Reviewed, New-added", "Not Reviewed, Amended", etc.
    topic: String  // High-level category (maps to CarePhase)
    subtopic: String  // Optional finer categorization
    rationale: String  // Optional explanation
    source_page: Integer  // Page reference in source document
}
```

### Strength-Direction Combined Values

| Value | Meaning |
|-------|---------|
| `Strong For` | Strong recommendation to do something |
| `Strong Against` | Strong recommendation to avoid something |
| `Weak For` | Weak/conditional recommendation to do something |
| `Weak Against` | Weak/conditional recommendation to avoid something |
| `Neither` | Insufficient evidence to recommend for or against |

### Category Values (Version Status)

| Value | Meaning |
|-------|---------|
| `Reviewed, New-added` | New recommendation added after evidence review |
| `Reviewed, New-replaced` | Replaced previous recommendation after evidence review |
| `Not Reviewed, Amended` | Minor amendment without full evidence review |
| `Reviewed, Amended` | Amended after evidence review |

### Relationships

| Relationship | Direction | Target | Description |
|--------------|-----------|--------|-------------|
| `BELONGS_TO` | Recommendation → CarePhase | Primary care phase this rec belongs to |
| `RELEVANT_TO` | Recommendation → CarePhase | Secondary care phases (cross-reference) |
| `BASED_ON` | Recommendation → EvidenceBody | Evidence supporting this rec |
| `RECOMMENDS` | Recommendation → Intervention | What action is recommended |
| `APPLIES_TO` | Recommendation → Condition | Only for sub-conditions/complications |

### Design Decisions

1. **Combined strength_direction**: Single enum instead of separate fields for simpler querying
2. **Primary + Secondary phases**: `BELONGS_TO` for primary, `RELEVANT_TO` for secondary phases
3. **APPLIES_TO only for sub-conditions**: Not used for primary guideline condition (implied by Guideline)
4. **No ordering**: Recommendations unordered within phase; sort by strength when displaying
5. **No direct KeyQuestion link**: Path goes through EvidenceBody (semantically correct)

### Example

```cypher
(:Recommendation {
    rec_id: "VA_DOD_T2DM_2023_REC_22",
    rec_number: 22,
    rec_text: "For adults with type 2 diabetes mellitus and chronic kidney disease, we recommend sodium-glucose cotransporter-2 inhibitors with proven renal protection to improve renal outcomes.",
    strength_direction: "Strong For",
    category: "Reviewed, New-added",
    topic: "Pharmacotherapy",
    subtopic: null,
    source_page: 26
})

// Relationships
(r:Recommendation)-[:BELONGS_TO]->(cp:CarePhase {phase_id: "INTERV"})
(r:Recommendation)-[:RELEVANT_TO]->(cp2:CarePhase {phase_id: "COMP"})
(r:Recommendation)-[:BASED_ON]->(eb:EvidenceBody {eb_id: "EB_KQ7"})
(r:Recommendation)-[:APPLIES_TO]->(c:Condition {name: "Diabetic Nephropathy"})
(r:Recommendation)-[:RECOMMENDS]->(i:Intervention {name: "SGLT2 inhibitors"})
```

---

## Level 3: Evidence Chain (GRADE/PICOT)

**Status**: ✅ Approved

### Purpose
The Evidence Chain represents how research evidence supports recommendations, following GRADE methodology with PICOT-structured questions.

### Key Question Node

```cypher
KeyQuestion {
    kq_id: String (unique)
    kq_number: Integer  // Sequential: 1, 2, 3...
    question_text: String  // Full PICOT-formatted question

    // PICOT elements
    population: String  // "Adults with T2DM and CKD"
    intervention: String  // "SGLT2 inhibitors"
    comparator: String  // "Standard care" or "Placebo"
    outcomes_critical: String[]  // Array: ["MACE", "Mortality"]
    outcomes_important: String[]  // Array: ["HbA1c", "Quality of life"]
    timing: String  // "Long-term", "Variable"
    setting: String  // "Primary care"

    // Metadata
    num_studies: Integer
    study_types: String[]  // ["RCT", "SR"]
}
```

### Evidence Body Node

```cypher
EvidenceBody {
    eb_id: String (unique)
    topic: String  // Subject area
    quality_rating: String  // "High", "Moderate", "Low", "Very Low", "Insufficient"
    num_studies: Integer
    study_types: String[]
    key_findings: String  // For embedding/semantic search

    // Future: GRADE quality factors (manual data entry)
    // risk_of_bias: String
    // inconsistency: String
    // indirectness: String
    // imprecision: String
    // effect_estimate: String
}
```

### Study Node

```cypher
Study {
    study_id: String (unique)
    pmid: String  // PubMed ID (for linking to PubMed)
    title: String
    authors: String
    journal: String
    year: Integer
    abstract: String  // For embedding - contains effect sizes in narrative form
    study_type: String  // "RCT", "Systematic Review", "Cohort", "Cross-sectional"
    mesh_terms: String[]  // MeSH headings from PubMed
    publication_types: String[]  // PubMed publication types
}
```

### Relationships

```
KeyQuestion <──ANSWERS── EvidenceBody <──INCLUDES── Study
```

| Relationship | Direction | Description |
|--------------|-----------|-------------|
| `ANSWERS` | EvidenceBody → KeyQuestion | Evidence synthesis answers this PICOT question |
| `INCLUDES` | EvidenceBody → Study | Studies included in this evidence synthesis |

**Note**: A single Study CAN be included in multiple Evidence Bodies (natural graph relationship).

### Design Decisions

1. **Outcomes as arrays**: `outcomes_critical` and `outcomes_important` stored as arrays on KeyQuestion for MVP. Can refactor to Outcome nodes later if cross-question querying becomes important.

2. **Shared studies**: Studies can have multiple incoming `INCLUDES` relationships from different Evidence Bodies. No duplication needed.

3. **Effect sizes deferred**: Study-level effect sizes (HR, CI, p-values) not modeled as discrete fields. The `abstract` field contains this information in narrative form and is embedded for semantic search.

4. **GRADE factors deferred**: Detailed quality domains (risk_of_bias, inconsistency, etc.) deferred to manual data entry phase. `quality_rating` summary is sufficient for MVP.

### Example

```cypher
// Key Question with full PICOT
(:KeyQuestion {
    kq_id: "VA_DOD_T2DM_2023_KQ7",
    kq_number: 7,
    question_text: "In adults with T2DM, what are the risks and benefits of treatment with either SGLT-2 inhibitors or GLP-1 receptor agonists on cardiovascular or renal outcomes?",
    population: "Adults with T2DM",
    intervention: "SGLT-2 inhibitors or GLP-1 receptor agonists",
    comparator: "Placebo or other diabetes medications",
    outcomes_critical: ["Cardiovascular outcomes", "Renal outcomes", "Mortality"],
    outcomes_important: ["HbA1c", "Weight", "Hypoglycemia"],
    timing: "Long-term",
    setting: "Primary care",
    num_studies: 9,
    study_types: ["SRs: 9"]
})

// Evidence Body answering the question
(:EvidenceBody {
    eb_id: "EB_KQ7",
    topic: "SGLT-2i and GLP-1 RA Outcomes",
    quality_rating: "High",
    num_studies: 9,
    study_types: ["Systematic review"],
    key_findings: "SGLT-2 inhibitors and GLP-1 RAs reduce cardiovascular and renal outcomes independent of glycemic control."
})

// Relationships
(eb:EvidenceBody)-[:ANSWERS]->(kq:KeyQuestion)
(eb:EvidenceBody)-[:INCLUDES]->(s:Study)
```

---

## Intervention Node (Cross-Cutting)

**Status**: ✅ Approved

### Purpose
Interventions represent clinical actions recommended by the guideline. They are hierarchical: drug classes contain individual drugs.

### Node Definition

```cypher
Intervention {
    intervention_id: String (unique)
    name: String  // "SGLT2 inhibitors" or "Empagliflozin"
    type: String  // "drug_class", "drug", "procedure", "lifestyle", "device", "referral"
    description: String  // Optional explanation

    // For drugs specifically
    drug_class: String  // If type="drug", parent class name
    mechanism: String  // Optional: mechanism of action
}
```

### Type Values

| Type | Description | Example |
|------|-------------|---------|
| `drug_class` | Category of medications | "SGLT2 inhibitors" |
| `drug` | Specific medication | "Empagliflozin" |
| `procedure` | Medical procedure | "Bariatric surgery" |
| `lifestyle` | Behavioral intervention | "Mediterranean diet" |
| `device` | Medical device | "Continuous glucose monitor" |
| `referral` | Referral to specialist | "Endocrinology referral" |

### Relationships

| Relationship | Direction | Description |
|--------------|-----------|-------------|
| `INCLUDES` | Intervention (class) → Intervention (drug) | Drug class contains specific drugs |
| `RECOMMENDS` | Recommendation → Intervention | Recommendation suggests this intervention |

### Example

```cypher
// Drug class
(:Intervention {
    intervention_id: "INT_SGLT2I",
    name: "SGLT2 inhibitors",
    type: "drug_class",
    mechanism: "Inhibits sodium-glucose cotransporter-2 in kidney"
})

// Individual drug
(:Intervention {
    intervention_id: "INT_EMPA",
    name: "Empagliflozin",
    type: "drug",
    drug_class: "SGLT2 inhibitors"
})

// Hierarchy
(class:Intervention {type: "drug_class"})-[:INCLUDES]->(drug:Intervention {type: "drug"})

// Recommendation link
(r:Recommendation)-[:RECOMMENDS]->(class:Intervention {name: "SGLT2 inhibitors"})
```

---

## Cross-Cutting: Conditions

**Status**: ✅ Approved

### Purpose
Conditions are disease entities that exist independently of any specific guideline. They represent diagnosable medical conditions with standardized coding (ICD-10). Conditions are **reusable across guidelines** — the same Condition node can be referenced by multiple guidelines.

### Node Definition

```cypher
Condition {
    condition_id: String (unique)
    name: String  // "Type 2 Diabetes Mellitus"
    icd10_codes: String[]  // ["E11", "E11.9"]
    snomed_ct: String  // Optional: SNOMED code
    definition: String  // Clinical definition (for embedding)
    diagnostic_criteria: String  // How it's diagnosed (narrative form)
}
```

### Condition-to-Condition Relationships

**Important semantic distinctions:**

| Relationship | Semantics | Use Case | Example |
|--------------|-----------|----------|---------|
| `PRECURSOR_TO` | Same disease continuum, severity staging | Upstream condition that may progress | Prediabetes → T2DM |
| `MAY_DEVELOP` | Downstream complication (not inevitable) | Condition that may develop as consequence | T2DM → Diabetic Nephropathy |
| `ASSOCIATED_WITH` | Co-occurrence, unclear causation | True comorbidity, bidirectional association | T2DM ↔ Depression |

**Key distinction:**
- `PRECURSOR_TO`: Severity progression on same disease spectrum (relatively rare across guidelines)
- `MAY_DEVELOP`: Causal but not deterministic — "may develop" captures uncertainty
- `ASSOCIATED_WITH`: Epidemiological association, may be bidirectional

### Guideline-to-Condition Relationships

| Relationship | Description |
|--------------|-------------|
| `PRIMARILY_ABOUT` | The main condition(s) this guideline addresses |
| `REFERENCES` | Any condition mentioned, with `role` property |

**Role values for REFERENCES:**

| Role | Description | Example |
|------|-------------|---------|
| `precursor` | Upstream condition on same disease continuum | Prediabetes |
| `complication` | Downstream condition that may develop | Diabetic Nephropathy, Retinopathy |
| `comorbidity` | Associated condition, unclear causation | Depression, NAFLD |
| `adverse_effect` | Caused by treatment | Hypoglycemia |
| `differential` | Condition to rule out | Type 1 Diabetes |

### Recommendation-to-Condition Relationships

| Relationship | Description |
|--------------|-------------|
| `APPLIES_TO` | Only for sub-conditions/complications (not primary guideline condition) |

**Design Decision**: Recommendations do NOT link to the primary condition (T2DM) — that's implied by the Guideline. `APPLIES_TO` is only used when a recommendation specifically targets a complication or comorbidity (e.g., "SGLT2i for CKD").

### Example Conditions for Diabetes Guideline

| Condition | ICD-10 | Guideline Role | Notes |
|-----------|--------|----------------|-------|
| Type 2 Diabetes Mellitus | E11, E11.9 | **primary** | Main guideline focus |
| Prediabetes | R73.03 | precursor | Severity staging (HbA1c 5.7-6.4%) |
| Diabetic Nephropathy / CKD | E11.21, N18.x | complication | May develop |
| Diabetic Retinopathy | E11.31 | complication | May develop |
| Cardiovascular Disease | I25.x | complication | May develop |
| Heart Failure | I50.x | complication | May develop |
| NAFLD/NASH | K76.0, K75.81 | comorbidity | Associated |
| Cognitive Impairment | F06.7 | comorbidity | Associated |
| Depression | F32.x | comorbidity | Associated |
| Hypoglycemia | E16.2 | adverse_effect | Treatment-related |
| Type 1 Diabetes | E10 | differential | Rule out |

### Condition Relationship Map (Diabetes Example)

```
                              ┌──MAY_DEVELOP──► Diabetic Nephropathy
                              │
                              ├──MAY_DEVELOP──► Diabetic Retinopathy
                              │
Prediabetes ──PRECURSOR_TO──► Type 2 Diabetes ──MAY_DEVELOP──► Cardiovascular Disease
                              │
                              ├──MAY_DEVELOP──► Heart Failure
                              │
                              ├──ASSOCIATED_WITH──► Depression
                              │
                              ├──ASSOCIATED_WITH──► Cognitive Impairment
                              │
                              └──ASSOCIATED_WITH──► NAFLD/NASH
```

### Example Cypher

```cypher
// Primary condition
(:Condition {
    condition_id: "COND_T2DM",
    name: "Type 2 Diabetes Mellitus",
    icd10_codes: ["E11", "E11.9"],
    definition: "A metabolic disorder characterized by hyperglycemia resulting from defects in insulin secretion, insulin action, or both.",
    diagnostic_criteria: "HbA1c ≥6.5%, or FPG ≥126 mg/dL, or 2-hour OGTT ≥200 mg/dL, or random glucose ≥200 mg/dL with symptoms"
})

// Precursor condition
(:Condition {
    condition_id: "COND_PREDM",
    name: "Prediabetes",
    icd10_codes: ["R73.03"],
    definition: "Intermediate state of hyperglycemia with glycemic parameters above normal but below diabetes threshold.",
    diagnostic_criteria: "HbA1c 5.7-6.4%, or FPG 100-125 mg/dL, or 2-hour OGTT 140-199 mg/dL"
})

// Complication
(:Condition {
    condition_id: "COND_DKD",
    name: "Diabetic Nephropathy",
    icd10_codes: ["E11.21", "N18.1", "N18.2", "N18.3", "N18.4", "N18.5"],
    definition: "Kidney disease caused by diabetes, characterized by albuminuria and progressive decline in GFR.",
    diagnostic_criteria: "Persistent albuminuria (UACR ≥30 mg/g) and/or eGFR <60 mL/min/1.73m² in setting of diabetes"
})

// Guideline relationships
(g:Guideline)-[:PRIMARILY_ABOUT]->(t2dm:Condition {name: "Type 2 Diabetes Mellitus"})
(g:Guideline)-[:REFERENCES {role: "precursor"}]->(predm:Condition {name: "Prediabetes"})
(g:Guideline)-[:REFERENCES {role: "complication"}]->(dkd:Condition {name: "Diabetic Nephropathy"})

// Condition-to-condition relationships
(predm:Condition)-[:PRECURSOR_TO]->(t2dm:Condition)
(t2dm:Condition)-[:MAY_DEVELOP]->(dkd:Condition)
(t2dm:Condition)-[:ASSOCIATED_WITH]->(dep:Condition {name: "Depression"})

// Recommendation targeting a specific complication
(r:Recommendation {rec_text: "...SGLT2i for CKD..."})-[:APPLIES_TO]->(dkd:Condition)
```

### Design Decisions

1. **Model all conditions**: All conditions mentioned in the guideline are modeled as nodes, categorized by role
2. **Diagnostic criteria as narrative**: Stored as text on Condition node for AI comprehension; can refactor to DiagnosticCriteria nodes later if structured queries needed
3. **Semantic relationship types**: `PRECURSOR_TO` vs `MAY_DEVELOP` vs `ASSOCIATED_WITH` capture important clinical distinctions
4. **Precursors are rare**: Most disease progressions are complications (`MAY_DEVELOP`), not staging (`PRECURSOR_TO`)
5. **Bidirectional associations**: `ASSOCIATED_WITH` can be traversed in either direction for comorbidities

---

## Indexing Strategy

**Status**: ✅ Approved

### Overview

Three types of indexes support different query patterns:

| Index Type | Purpose | Use Case |
|------------|---------|----------|
| **Unique Constraints** | Data integrity + fast ID lookup | Find node by ID |
| **Property Indexes** | Fast filtering by property values | Filter by type, year, strength |
| **Full-Text Indexes** | Keyword search in text fields | "Find recommendations mentioning SGLT2" |
| **Vector Indexes** | Semantic similarity search | "Recommendations about kidney protection" |

### Unique Constraints (8)

Required for data integrity. Automatically create indexes on the constrained property.

```cypher
CREATE CONSTRAINT guideline_id_unique FOR (g:Guideline) REQUIRE g.guideline_id IS UNIQUE;
CREATE CONSTRAINT carephase_id_unique FOR (cp:CarePhase) REQUIRE cp.phase_id IS UNIQUE;
CREATE CONSTRAINT recommendation_id_unique FOR (r:Recommendation) REQUIRE r.rec_id IS UNIQUE;
CREATE CONSTRAINT keyquestion_id_unique FOR (kq:KeyQuestion) REQUIRE kq.kq_id IS UNIQUE;
CREATE CONSTRAINT evidencebody_id_unique FOR (eb:EvidenceBody) REQUIRE eb.eb_id IS UNIQUE;
CREATE CONSTRAINT study_id_unique FOR (s:Study) REQUIRE s.study_id IS UNIQUE;
CREATE CONSTRAINT intervention_id_unique FOR (i:Intervention) REQUIRE i.intervention_id IS UNIQUE;
CREATE CONSTRAINT condition_id_unique FOR (c:Condition) REQUIRE c.condition_id IS UNIQUE;
```

### Property Indexes (10)

Support common query patterns for filtering and lookup.

```cypher
// Study lookups and filters
CREATE INDEX study_pmid FOR (s:Study) ON (s.pmid);
CREATE INDEX study_year FOR (s:Study) ON (s.year);
CREATE INDEX study_type FOR (s:Study) ON (s.study_type);

// Recommendation filters
CREATE INDEX rec_strength FOR (r:Recommendation) ON (r.strength_direction);
CREATE INDEX rec_category FOR (r:Recommendation) ON (r.category);

// Evidence quality filter
CREATE INDEX eb_quality FOR (eb:EvidenceBody) ON (eb.quality_rating);

// Intervention lookups
CREATE INDEX intervention_type FOR (i:Intervention) ON (i.type);
CREATE INDEX intervention_name FOR (i:Intervention) ON (i.name);

// Condition lookups
CREATE INDEX condition_name FOR (c:Condition) ON (c.name);
CREATE INDEX condition_icd10 FOR (c:Condition) ON (c.icd10_codes);
```

**Note on ICD-10 array index**: Queries use `WHERE "E11" IN c.icd10_codes`. Less efficient than traversal but simpler for MVP.

### Full-Text Indexes (3)

Keyword search for structured/shorter text where semantic search is less effective.

```cypher
// Primary clinical query surface
CREATE FULLTEXT INDEX recommendation_fulltext FOR (r:Recommendation) ON EACH [r.rec_text];

// Care phases - clinical pathway queries
CREATE FULLTEXT INDEX carephase_fulltext FOR (cp:CarePhase) ON EACH [cp.name, cp.description];

// Conditions - disease/diagnosis queries
CREATE FULLTEXT INDEX condition_fulltext FOR (c:Condition) ON EACH [c.name, c.definition, c.diagnostic_criteria];
```

**Usage:**
```cypher
// Find recommendations mentioning "SGLT2"
CALL db.index.fulltext.queryNodes("recommendation_fulltext", "SGLT2") YIELD node, score
RETURN node.rec_text, score ORDER BY score DESC

// Find care phases related to "screening"
CALL db.index.fulltext.queryNodes("carephase_fulltext", "screening") YIELD node, score
RETURN node.name, score ORDER BY score DESC

// Find conditions by symptom/criteria
CALL db.index.fulltext.queryNodes("condition_fulltext", "HbA1c") YIELD node, score
RETURN node.name, score ORDER BY score DESC
```

**Design Decision**: Full-text for CarePhase and Condition because their text is shorter/more structured — better suited for keyword search than semantic similarity.

### Design Decisions

1. **No composite indexes**: Single-property indexes sufficient for MVP query patterns
2. **ICD-10 as array**: Index array directly rather than separate lookup nodes
3. **Full-text for structured queries**: Recommendation, CarePhase, Condition (keyword search)
4. **Vector for semantic queries**: See Embedding Strategy section

---

## Embedding Strategy

**Status**: ✅ Approved

### Overview

Vector embeddings enable semantic search — finding content by meaning rather than exact keywords. Used for rich text content where meaning matters more than keywords.

### Technical Approach

| Aspect | Choice |
|--------|--------|
| **Model** | `text-embedding-3-small` (OpenAI) |
| **Dimensions** | 1536 |
| **Generation** | Neo4j GenAI plugin (server-side) |
| **Similarity** | Cosine via `vector.similarity.cosine()` |
| **Storage** | Property on node (e.g., `embedding`) |

### What Gets Embedded

Semantic search is best for **rich, natural language text** where meaning matters:

| Node Type | Embedded Field | Rationale |
|-----------|----------------|-----------|
| Recommendation | rec_text | Primary clinical query surface |
| Study | abstract | Rich research content |
| KeyQuestion | question_text | PICOT questions |
| EvidenceBody | key_findings | Synthesized conclusions |

### What Uses Full-Text Instead

Shorter/more structured text is better suited for **keyword search**:

| Node Type | Full-Text Fields | Rationale |
|-----------|------------------|-----------|
| CarePhase | name, description | Short clinical pathway terms |
| Condition | name, definition, diagnostic_criteria | Structured medical terminology |

### What Is Skipped for MVP

| Node Type | Reason |
|-----------|--------|
| Intervention | Reached via Recommendations; not primary query target |
| Guideline | Queried by ID, not semantically |

### Vector Indexes

```cypher
// Create vector indexes for embedded node types
CREATE VECTOR INDEX recommendation_embedding FOR (r:Recommendation) ON (r.embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 1536,
  `vector.similarity_function`: 'cosine'
}};

CREATE VECTOR INDEX study_embedding FOR (s:Study) ON (s.embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 1536,
  `vector.similarity_function`: 'cosine'
}};

CREATE VECTOR INDEX keyquestion_embedding FOR (kq:KeyQuestion) ON (kq.embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 1536,
  `vector.similarity_function`: 'cosine'
}};

CREATE VECTOR INDEX evidencebody_embedding FOR (eb:EvidenceBody) ON (eb.embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 1536,
  `vector.similarity_function`: 'cosine'
}};
```

### Embedding Generation

Using Neo4j GenAI plugin (server-side):

```cypher
// Generate embeddings for recommendations
MATCH (r:Recommendation) WHERE r.embedding IS NULL
WITH r, r.rec_text AS text
CALL genai.vector.encode(text, "OpenAI", {model: "text-embedding-3-small"}) YIELD vector
SET r.embedding = vector
RETURN count(r) AS embedded_count;
```

### Design Decisions

1. **Single field per node**: Embed one primary field (not concatenated) for MVP simplicity
2. **Semantic vs Full-Text split**: Rich narrative text → vector; short/structured text → full-text
3. **Intervention deferred**: Users find interventions through recommendations, not direct search
4. **Server-side generation**: GenAI plugin avoids Python SDK complexity, handles batching

---

## Change Log

| Date | Level | Decision |
|------|-------|----------|
| 2026-02-05 | Level 0 | Approved hybrid approach: rich Guideline metadata + typed Condition relationships |
| 2026-02-05 | Two Hierarchies | Approved: Clinical Care Structure + Evidence Structure with BASED_ON bridge |
| 2026-02-05 | Level 1 | Approved: 6 care phases (combined treatments into "Interventions") |
| 2026-02-05 | Level 1 | Decision: Comparator lives in KeyQuestion (PICOT "C"), not as a Care Phase |
| 2026-02-05 | Level 1 | Decision: No direct Recommendation → KeyQuestion relationship (intentional) |
| 2026-02-05 | Level 2 | Approved: Combined strength_direction enum, category field for version status |
| 2026-02-05 | Level 2 | Decision: Primary BELONGS_TO + Secondary RELEVANT_TO for multi-phase recs |
| 2026-02-05 | Level 2 | Decision: APPLIES_TO only for sub-conditions (CKD, retinopathy, etc.) |
| 2026-02-05 | Level 3 | Approved: KeyQuestion with full PICOT arrays, EvidenceBody, Study |
| 2026-02-05 | Level 3 | Decision: Outcomes as arrays for MVP (can refactor to nodes later) |
| 2026-02-05 | Level 3 | Decision: Studies can be shared across Evidence Bodies (multiple INCLUDES) |
| 2026-02-05 | Level 3 | Decision: Effect sizes deferred - abstract contains narrative form |
| 2026-02-05 | Intervention | Approved: Hierarchical structure (drug_class → drug, plus procedure/lifestyle/device/referral) |
| 2026-02-05 | Conditions | Approved: ICD-10 coded disease entities, reusable across guidelines |
| 2026-02-05 | Conditions | Decision: Three relationship types - PRECURSOR_TO, MAY_DEVELOP, ASSOCIATED_WITH |
| 2026-02-05 | Conditions | Decision: Diagnostic criteria as narrative text for MVP (can refactor to nodes later) |
| 2026-02-05 | Conditions | Decision: APPLIES_TO only for sub-conditions, not primary guideline condition |
| 2026-02-05 | Indexing | Approved: 8 unique constraints, 10 property indexes, 3 full-text indexes |
| 2026-02-05 | Indexing | Decision: ICD-10 array indexed directly (simpler for MVP) |
| 2026-02-05 | Indexing | Decision: Full-text for Recommendation, CarePhase, Condition (keyword search) |
| 2026-02-05 | Embedding | Approved: Vector embeddings for Recommendation, Study, KeyQuestion, EvidenceBody |
| 2026-02-05 | Embedding | Decision: CarePhase/Condition use full-text (short/structured text) |
| 2026-02-05 | Embedding | Decision: Skip Intervention embedding for MVP (reached via Recommendations) |
