# HiGraph-CPG Schema Documentation

## Overview

This document provides the complete technical specification for the HiGraph-CPG graph database schema. The schema is designed to represent clinical practice guidelines as an interconnected knowledge graph optimized for AI-powered traversal and clinical decision support.

**Schema Version**: 1.0  
**Database**: Neo4j 5.x  
**Last Updated**: February 4, 2026

---

## Design Principles

1. **Evidence Traceability**: Every recommendation traces back through evidence bodies to individual studies
2. **Clinical Context**: Patient characteristics and clinical scenarios are first-class entities
3. **Benefit-Harm Separation**: Benefits and adverse events are distinct entities for clear risk-benefit analysis
4. **Versioning Support**: All entities support temporal versioning for guideline updates
5. **AI-First**: Properties and relationships optimized for both semantic and syntactic queries
6. **Multi-Disease**: Schema is disease-agnostic and extends to any clinical domain

---

## Node Types

### 1. GUIDELINE

**Purpose**: Top-level container for a disease/condition-specific clinical practice guideline

**Label**: `Guideline`

**Properties**:
| Property | Type | Required | Unique | Description |
|----------|------|----------|--------|-------------|
| guideline_id | String | Yes | Yes | Unique identifier (e.g., "CPG_DM_2023") |
| disease_condition | String | Yes | No | Disease name (e.g., "Type 2 Diabetes Mellitus") |
| version | String | Yes | No | Version number (e.g., "6.0") |
| publication_date | Date | Yes | No | Official publication date |
| review_cycle_months | Integer | No | No | Scheduled review frequency in months |
| status | String | Yes | No | Enum: "Active", "Superseded", "Under Review" |
| organization | String | Yes | No | Publishing organization (e.g., "VA/DoD") |
| full_title | String | Yes | No | Complete guideline title |
| scope_description | String | No | No | High-level description of guideline scope |

**Constraints**:
```cypher
CREATE CONSTRAINT guideline_id_unique IF NOT EXISTS
FOR (g:Guideline) REQUIRE g.guideline_id IS UNIQUE;

CREATE CONSTRAINT guideline_required_props IF NOT EXISTS
FOR (g:Guideline) REQUIRE (g.guideline_id, g.disease_condition, g.version, g.publication_date, g.status, g.organization, g.full_title) IS NOT NULL;
```

**Indexes**:
```cypher
CREATE INDEX guideline_disease IF NOT EXISTS
FOR (g:Guideline) ON (g.disease_condition);

CREATE INDEX guideline_status IF NOT EXISTS
FOR (g:Guideline) ON (g.status);
```

**Example**:
```cypher
CREATE (g:Guideline {
  guideline_id: "CPG_DM_2023",
  disease_condition: "Type 2 Diabetes Mellitus",
  version: "6.0",
  publication_date: date("2023-05-01"),
  review_cycle_months: 36,
  status: "Active",
  organization: "VA/DoD",
  full_title: "VA/DoD Clinical Practice Guideline for the Management of Type 2 Diabetes Mellitus",
  scope_description: "Evidence-based recommendations for T2DM management in adult VA/DoD populations"
})
```

---

### 2. CLINICAL_MODULE

**Purpose**: Major topic areas within a guideline (e.g., Pharmacotherapy, Screening, Self-Management)

**Label**: `ClinicalModule`

**Properties**:
| Property | Type | Required | Unique | Description |
|----------|------|----------|--------|-------------|
| module_id | String | Yes | Yes | Unique identifier (e.g., "MOD_PHARM_001") |
| module_name | String | Yes | No | Topic name (e.g., "Pharmacotherapy") |
| description | String | No | No | Brief description of module scope |
| guideline_id | String | Yes | No | Parent guideline reference |
| sequence_order | Integer | No | No | Display order within guideline |

**Constraints**:
```cypher
CREATE CONSTRAINT module_id_unique IF NOT EXISTS
FOR (m:ClinicalModule) REQUIRE m.module_id IS UNIQUE;
```

**Relationships**:
- `(ClinicalModule)-[:PART_OF]->(Guideline)`
- `(ClinicalModule)-[:CONTAINS]->(KeyQuestion)`

**Example**:
```cypher
CREATE (m:ClinicalModule {
  module_id: "MOD_PHARM_001",
  module_name: "Pharmacotherapy",
  description: "Medication management for glycemic control",
  guideline_id: "CPG_DM_2023",
  sequence_order: 3
})
```

---

### 3. KEY_QUESTION

**Purpose**: PICOTS-based research questions that guide systematic evidence review

**Label**: `KeyQuestion`

**Properties**:
| Property | Type | Required | Unique | Description |
|----------|------|----------|--------|-------------|
| kq_id | String | Yes | Yes | Unique identifier (e.g., "KQ_001") |
| kq_number | Integer | Yes | No | Sequential question number |
| question_text | String | Yes | No | Full question text |
| population | String | Yes | No | PICOTS: Target population description |
| intervention | String | Yes | No | PICOTS: Intervention(s) of interest |
| comparator | String | No | No | PICOTS: Comparison group |
| outcomes_critical | List[String] | Yes | No | PICOTS: Critical outcomes for decision making |
| outcomes_important | List[String] | No | No | PICOTS: Important but not critical outcomes |
| timing | String | No | No | PICOTS: Time frame of interest |
| setting | String | No | No | PICOTS: Clinical setting |
| module_id | String | Yes | No | Parent module reference |
| guideline_id | String | Yes | No | Parent guideline reference |

**Constraints**:
```cypher
CREATE CONSTRAINT kq_id_unique IF NOT EXISTS
FOR (kq:KeyQuestion) REQUIRE kq.kq_id IS UNIQUE;
```

**Relationships**:
- `(KeyQuestion)-[:ADDRESSES]->(ClinicalModule)`
- `(KeyQuestion)-[:ANSWERED_BY]->(EvidenceBody)`
- `(KeyQuestion)-[:LEADS_TO]->(Recommendation)`

**Example**:
```cypher
CREATE (kq:KeyQuestion {
  kq_id: "KQ_001",
  kq_number: 1,
  question_text: "In adults with T2DM, what impact does glycemic variability have on outcomes?",
  population: "Nonpregnant adults age ≥18 with T2DM",
  intervention: "Measurement and management of glycemic variability",
  comparator: "Standard care without variability assessment",
  outcomes_critical: ["CV mortality", "Hypoglycemia", "All-cause mortality"],
  outcomes_important: ["HbA1c", "Quality of life"],
  timing: "Short-term and long-term outcomes",
  setting: "Primary care, outpatient",
  module_id: "MOD_GLYCEMIC_001",
  guideline_id: "CPG_DM_2023"
})
```

---

### 4. EVIDENCE_BODY

**Purpose**: Synthesized evidence from multiple studies addressing a key question

**Label**: `EvidenceBody`

**Properties**:
| Property | Type | Required | Unique | Description |
|----------|------|----------|--------|-------------|
| evidence_id | String | Yes | Yes | Unique identifier (e.g., "EVB_001") |
| topic | String | Yes | No | Evidence topic summary |
| quality_rating | String | Yes | No | GRADE: "High", "Moderate", "Low", "Very Low" |
| confidence_level | String | Yes | No | Confidence description |
| num_studies | Integer | Yes | No | Number of studies synthesized |
| study_types | List[String] | Yes | No | Types of studies included (e.g., ["RCT", "SR"]) |
| date_synthesized | Date | Yes | No | When evidence was reviewed |
| population_description | String | Yes | No | Population characteristics from studies |
| key_findings | String | Yes | No | Summary of synthesized findings |
| guideline_id | String | Yes | No | Parent guideline reference |
| kq_id | String | Yes | No | Key question reference |
| version | String | Yes | No | Evidence synthesis version |

**Constraints**:
```cypher
CREATE CONSTRAINT evidence_id_unique IF NOT EXISTS
FOR (eb:EvidenceBody) REQUIRE eb.evidence_id IS UNIQUE;
```

**Relationships**:
- `(EvidenceBody)-[:SYNTHESIZES]->(Study)`
- `(EvidenceBody)-[:ANSWERS]->(KeyQuestion)`
- `(EvidenceBody)-[:SUPPORTS]->(Recommendation)`
- `(EvidenceBody)-[:EVALUATED_BY]->(QualityAssessment)`

**Example**:
```cypher
CREATE (eb:EvidenceBody {
  evidence_id: "EVB_001",
  topic: "Metformin efficacy and safety in T2DM",
  quality_rating: "High",
  confidence_level: "High confidence in estimate of effect",
  num_studies: 12,
  study_types: ["RCT", "Systematic Review"],
  date_synthesized: date("2022-04-11"),
  population_description: "Adults with T2DM in primary care settings",
  key_findings: "Metformin reduces HbA1c by 1.5% vs placebo with low risk of hypoglycemia",
  guideline_id: "CPG_DM_2023",
  kq_id: "KQ_005",
  version: "6.0"
})
```

---

### 5. STUDY

**Purpose**: Individual research study (RCT, systematic review, observational study)

**Label**: `Study`

**Properties**:
| Property | Type | Required | Unique | Description |
|----------|------|----------|--------|-------------|
| study_id | String | Yes | Yes | Internal unique identifier |
| pmid | String | No | No | PubMed ID if available |
| doi | String | No | No | Digital Object Identifier |
| title | String | Yes | No | Study title |
| authors | String | Yes | No | Author list |
| journal | String | Yes | No | Journal name |
| year | Integer | Yes | No | Publication year |
| study_type | String | Yes | No | Enum: "RCT", "Systematic Review", "Cohort", "Cross-sectional" |
| study_quality | String | Yes | No | USPSTF rating: "Good", "Fair", "Poor" |
| sample_size | Integer | No | No | Number of participants |
| duration_weeks | Integer | No | No | Study duration in weeks |
| setting | String | No | No | Study setting description |
| country | String | No | No | Country or "Multi-national" |
| abstract | String | No | No | Study abstract text |

**Constraints**:
```cypher
CREATE CONSTRAINT study_id_unique IF NOT EXISTS
FOR (s:Study) REQUIRE s.study_id IS UNIQUE;

CREATE INDEX study_pmid IF NOT EXISTS
FOR (s:Study) ON (s.pmid);
```

**Relationships**:
- `(Study)-[:INCLUDED_IN]->(EvidenceBody)`
- `(Study)-[:MEASURES]->(OutcomeMeasurement)`
- `(Study)-[:COMPARES {vs: String}]->(Intervention)` - vs property describes comparison
- `(Study)-[:ENROLLS]->(PatientPopulation)`
- `(Study)-[:DEMONSTRATES]->(Benefit)`
- `(Study)-[:DEMONSTRATES]->(AdverseEvent)`

**Example**:
```cypher
CREATE (s:Study {
  study_id: "STUDY_UKPDS34",
  pmid: "9742976",
  doi: "10.1016/S0140-6736(98)07037-8",
  title: "Effect of intensive blood-glucose control with metformin on complications in overweight patients with type 2 diabetes (UKPDS 34)",
  authors: "UK Prospective Diabetes Study Group",
  journal: "Lancet",
  year: 1998,
  study_type: "RCT",
  study_quality: "Good",
  sample_size: 753,
  duration_weeks: 520,
  setting: "Primary care",
  country: "United Kingdom"
})
```

---

### 6. RECOMMENDATION

**Purpose**: Clinical action statement derived from evidence

**Label**: `Recommendation`

**Properties**:
| Property | Type | Required | Unique | Description |
|----------|------|----------|--------|-------------|
| rec_id | String | Yes | Yes | Unique identifier (e.g., "REC_001") |
| rec_number | Integer | Yes | No | Sequential recommendation number |
| rec_text | String | Yes | No | Complete recommendation statement |
| strength | String | Yes | No | GRADE: "Strong", "Weak" |
| direction | String | Yes | No | Enum: "For", "Against", "Neither" |
| category | String | Yes | No | Enum: "New-added", "New-replaced", "Not changed", "Amended", "Deleted" |
| topic | String | Yes | No | Topic/subtopic classification |
| subtopic | String | No | No | More specific classification |
| module_id | String | Yes | No | Parent clinical module |
| guideline_id | String | Yes | No | Parent guideline reference |
| version | String | Yes | No | Recommendation version |
| version_date | Date | Yes | No | Date of this version |
| previous_version_id | String | No | No | Link to superseded recommendation |
| status | String | Yes | No | Enum: "Active", "Superseded", "Under Review" |
| implementation_considerations | String | No | No | Practical implementation notes |

**Constraints**:
```cypher
CREATE CONSTRAINT rec_id_unique IF NOT EXISTS
FOR (r:Recommendation) REQUIRE r.rec_id IS UNIQUE;

CREATE INDEX rec_strength IF NOT EXISTS
FOR (r:Recommendation) ON (r.strength);

CREATE INDEX rec_status IF NOT EXISTS
FOR (r:Recommendation) ON (r.status);
```

**Relationships**:
- `(Recommendation)-[:BASED_ON]->(EvidenceBody)`
- `(Recommendation)-[:ADDRESSES]->(KeyQuestion)`
- `(Recommendation)-[:APPLIES_TO]->(ClinicalScenario)`
- `(Recommendation)-[:RECOMMENDS]->(Intervention)`
- `(Recommendation)-[:MODIFIED_BY]->(PatientCharacteristic)` - strengthens/weakens
- `(Recommendation)-[:CONFLICTS_WITH]->(Recommendation)`
- `(Recommendation)-[:SUPERSEDES]->(Recommendation)`
- `(Recommendation)-[:DETERMINED_BY]->(DecisionFramework)`

**Example**:
```cypher
CREATE (r:Recommendation {
  rec_id: "REC_007",
  rec_number: 7,
  rec_text: "In adults with type 2 diabetes mellitus, we recommend diabetes self-management education and support.",
  strength: "Strong",
  direction: "For",
  category: "Not changed",
  topic: "Diabetes Self-Management Education and Support",
  subtopic: null,
  module_id: "MOD_DSME_001",
  guideline_id: "CPG_DM_2023",
  version: "6.0",
  version_date: date("2023-05-01"),
  previous_version_id: "REC_007_v5",
  status: "Active",
  implementation_considerations: "DSME programs widely available in VA/DoD facilities"
})
```

---

### 7. CLINICAL_SCENARIO

**Purpose**: Point-of-care clinical context that triggers specific recommendations

**Label**: `ClinicalScenario`

**Properties**:
| Property | Type | Required | Unique | Description |
|----------|------|----------|--------|-------------|
| scenario_id | String | Yes | Yes | Unique identifier (e.g., "CS_001") |
| name | String | Yes | No | Brief scenario name |
| description | String | Yes | No | Detailed scenario description |
| prevalence | String | No | No | How common: "Common", "Uncommon", "Rare" |
| urgency | String | No | No | Clinical urgency: "Emergency", "Urgent", "Routine" |
| decision_points | List[String] | No | No | Key decisions in this scenario |
| guideline_id | String | Yes | No | Parent guideline reference |

**Constraints**:
```cypher
CREATE CONSTRAINT scenario_id_unique IF NOT EXISTS
FOR (cs:ClinicalScenario) REQUIRE cs.scenario_id IS UNIQUE;
```

**Relationships**:
- `(ClinicalScenario)-[:TRIGGERS]->(Recommendation)`
- `(ClinicalScenario)-[:REQUIRES]->(PatientCharacteristic)`
- `(ClinicalScenario)-[:PART_OF]->(ClinicalModule)`

**Example**:
```cypher
CREATE (cs:ClinicalScenario {
  scenario_id: "CS_001",
  name: "Newly diagnosed T2DM, no complications",
  description: "Adult patient with recent T2DM diagnosis, no known microvascular or macrovascular complications, eGFR >60",
  prevalence: "Common",
  urgency: "Routine",
  decision_points: ["First-line therapy selection", "Glycemic target setting", "Monitoring frequency"],
  guideline_id: "CPG_DM_2023"
})
```

---

### 8. INTERVENTION

**Purpose**: Treatment, action, or therapy that can be recommended

**Label**: `Intervention`

**Properties**:
| Property | Type | Required | Unique | Description |
|----------|------|----------|--------|-------------|
| intervention_id | String | Yes | Yes | Unique identifier (e.g., "INT_METFORMIN") |
| name | String | Yes | No | Intervention name |
| generic_name | String | No | No | Generic drug name if applicable |
| drug_class | String | No | No | Pharmacologic class (e.g., "Biguanide") |
| type | String | Yes | No | Enum: "Pharmacologic", "Non-pharmacologic", "Procedural" |
| mechanism | String | No | No | Mechanism of action |
| typical_dose | String | No | No | Typical dosing |
| administration | String | No | No | Route of administration |
| cost_category | String | No | No | Enum: "Low", "Moderate", "High" |
| availability | String | No | No | Availability notes (e.g., "Generic available") |

**Constraints**:
```cypher
CREATE CONSTRAINT intervention_id_unique IF NOT EXISTS
FOR (i:Intervention) REQUIRE i.intervention_id IS UNIQUE;

CREATE INDEX intervention_name IF NOT EXISTS
FOR (i:Intervention) ON (i.name);

CREATE INDEX intervention_class IF NOT EXISTS
FOR (i:Intervention) ON (i.drug_class);
```

**Relationships**:
- `(Intervention)-[:COMPARED_IN]->(Study)`
- `(Intervention)-[:PRODUCES]->(Benefit)`
- `(Intervention)-[:CAUSES]->(AdverseEvent)`
- `(Intervention)-[:CONTRAINDICATED_BY]->(Contraindication)`
- `(Intervention)-[:ALTERNATIVE_TO]->(Intervention)`
- `(Intervention)-[:COMBINES_WITH]->(Intervention)` - for combination therapy

**Example**:
```cypher
CREATE (i:Intervention {
  intervention_id: "INT_METFORMIN",
  name: "Metformin",
  generic_name: "Metformin hydrochloride",
  drug_class: "Biguanide",
  type: "Pharmacologic",
  mechanism: "Decreases hepatic glucose production, improves insulin sensitivity",
  typical_dose: "500-2000 mg daily",
  administration: "Oral",
  cost_category: "Low",
  availability: "Generic available"
})
```

---

### 9. OUTCOME

**Purpose**: Measured clinical endpoint (neutral/general category)

**Label**: `Outcome`

**Properties**:
| Property | Type | Required | Unique | Description |
|----------|------|----------|--------|-------------|
| outcome_id | String | Yes | Yes | Unique identifier (e.g., "OUT_HBA1C") |
| name | String | Yes | No | Outcome name |
| description | String | Yes | No | Detailed outcome description |
| measurement_method | String | No | No | How outcome is measured |
| criticality | String | Yes | No | GRADE: "Critical" (7-9), "Important" (4-6), "Limited" (1-3) |
| outcome_category | String | No | No | General category (e.g., "Glycemic", "Cardiovascular", "Safety") |

**Constraints**:
```cypher
CREATE CONSTRAINT outcome_id_unique IF NOT EXISTS
FOR (o:Outcome) REQUIRE o.outcome_id IS UNIQUE;
```

**Relationships**:
- `(Outcome)-[:PRIORITIZED_IN]->(KeyQuestion)`
- `(Outcome)-[:MEASURED_BY]->(Study)`

**Example**:
```cypher
CREATE (o:Outcome {
  outcome_id: "OUT_HBA1C",
  name: "HbA1c",
  description: "Glycated hemoglobin A1c",
  measurement_method: "Laboratory assay, percentage or mmol/mol",
  criticality: "Critical",
  outcome_category: "Glycemic"
})
```

---

### 10. OUTCOME_MEASUREMENT

**Purpose**: Specific measurement of an outcome in a particular study

**Label**: `OutcomeMeasurement`

**Properties**:
| Property | Type | Required | Unique | Description |
|----------|------|----------|--------|-------------|
| measurement_id | String | Yes | Yes | Unique identifier |
| study_id | String | Yes | No | Parent study reference |
| outcome_id | String | Yes | No | Outcome being measured |
| intervention_id | String | Yes | No | Intervention group |
| comparator_id | String | No | No | Comparison group if applicable |
| value | String | Yes | No | Measured value with units |
| value_numeric | Float | No | No | Numeric value if applicable |
| unit | String | No | No | Unit of measurement |
| timeframe | String | Yes | No | When measured (e.g., "30 weeks") |
| statistical_significance | String | No | No | P-value or CI |
| effect_size | String | No | No | Effect size description |

**Constraints**:
```cypher
CREATE CONSTRAINT measurement_id_unique IF NOT EXISTS
FOR (om:OutcomeMeasurement) REQUIRE om.measurement_id IS UNIQUE;
```

**Relationships**:
- `(OutcomeMeasurement)-[:MEASURES]->(Outcome)`
- `(OutcomeMeasurement)-[:FROM_STUDY]->(Study)`
- `(OutcomeMeasurement)-[:FOR_INTERVENTION]->(Intervention)`
- `(OutcomeMeasurement)-[:VS_COMPARATOR]->(Comparator)`

**Example**:
```cypher
CREATE (om:OutcomeMeasurement {
  measurement_id: "MEAS_UKPDS_HBA1C",
  study_id: "STUDY_UKPDS34",
  outcome_id: "OUT_HBA1C",
  intervention_id: "INT_METFORMIN",
  comparator_id: "COMP_CONVENTIONAL",
  value: "-1.5%",
  value_numeric: -1.5,
  unit: "percentage points",
  timeframe: "10 years median follow-up",
  statistical_significance: "p<0.001",
  effect_size: "Large clinically significant reduction"
})
```

---

### 11. BENEFIT

**Purpose**: Positive effect or desirable outcome from an intervention

**Label**: `Benefit`

**Properties**:
| Property | Type | Required | Unique | Description |
|----------|------|----------|--------|-------------|
| benefit_id | String | Yes | Yes | Unique identifier (e.g., "BEN_001") |
| name | String | Yes | No | Benefit name |
| description | String | Yes | No | Detailed benefit description |
| magnitude | String | No | No | Effect magnitude (e.g., "1.5% reduction") |
| magnitude_type | String | No | No | Type of magnitude: "Absolute", "Relative", "NNT" |
| criticality | String | Yes | No | GRADE: "Critical", "Important", "Limited" |
| timeframe | String | No | No | When benefit occurs |
| confidence | String | No | No | Confidence in benefit: "High", "Moderate", "Low" |
| clinical_significance | String | Yes | No | Is this clinically meaningful? |

**Constraints**:
```cypher
CREATE CONSTRAINT benefit_id_unique IF NOT EXISTS
FOR (b:Benefit) REQUIRE b.benefit_id IS UNIQUE;
```

**Relationships**:
- `(Benefit)-[:PRODUCED_BY]->(Intervention)`
- `(Benefit)-[:DEMONSTRATED_IN]->(Study)`
- `(Benefit)-[:SUPPORTED_BY]->(EvidenceBody)`

**Example**:
```cypher
CREATE (b:Benefit {
  benefit_id: "BEN_METFORMIN_HBA1C",
  name: "HbA1c reduction",
  description: "Decrease in glycated hemoglobin with metformin therapy",
  magnitude: "1.5%",
  magnitude_type: "Absolute reduction",
  criticality: "Critical",
  timeframe: "3-6 months",
  confidence: "High",
  clinical_significance: "Clinically meaningful reduction associated with decreased microvascular complications"
})
```

---

### 12. ADVERSE_EVENT

**Purpose**: Harm, negative effect, or undesirable outcome from an intervention

**Label**: `AdverseEvent`

**Properties**:
| Property | Type | Required | Unique | Description |
|----------|------|----------|--------|-------------|
| ae_id | String | Yes | Yes | Unique identifier (e.g., "AE_001") |
| name | String | Yes | No | Adverse event name |
| description | String | Yes | No | Detailed AE description |
| severity | String | Yes | No | Enum: "Mild", "Moderate", "Severe", "Life-threatening" |
| frequency | String | No | No | How common (e.g., "20-30%", "Rare") |
| frequency_type | String | No | No | Type: "Percentage", "Per patient-years", "Absolute number" |
| onset | String | No | No | When AE typically occurs |
| duration | String | No | No | How long AE lasts |
| management | String | No | No | How to manage/mitigate the AE |
| criticality | String | Yes | No | GRADE: "Critical", "Important", "Limited" |
| reversibility | String | No | No | Is AE reversible? "Reversible", "Irreversible", "Variable" |

**Constraints**:
```cypher
CREATE CONSTRAINT ae_id_unique IF NOT EXISTS
FOR (ae:AdverseEvent) REQUIRE ae.ae_id IS UNIQUE;
```

**Relationships**:
- `(AdverseEvent)-[:CAUSED_BY]->(Intervention)`
- `(AdverseEvent)-[:DEMONSTRATED_IN]->(Study)`
- `(AdverseEvent)-[:SUPPORTED_BY]->(EvidenceBody)`
- `(AdverseEvent)-[:RISK_INCREASED_BY]->(PatientCharacteristic)`

**Example**:
```cypher
CREATE (ae:AdverseEvent {
  ae_id: "AE_METFORMIN_GI",
  name: "Gastrointestinal side effects",
  description: "Nausea, diarrhea, abdominal discomfort associated with metformin",
  severity: "Mild to Moderate",
  frequency: "20-30%",
  frequency_type: "Percentage of patients",
  onset: "Early (first few weeks)",
  duration: "Usually transient, resolves with continued use or dose reduction",
  management: "Start low dose, titrate slowly, take with food, consider extended-release formulation",
  criticality: "Important",
  reversibility: "Reversible"
})
```

---

### 13. PATIENT_POPULATION

**Purpose**: Target demographic group for a recommendation or study

**Label**: `PatientPopulation`

**Properties**:
| Property | Type | Required | Unique | Description |
|----------|------|----------|--------|-------------|
| population_id | String | Yes | Yes | Unique identifier (e.g., "POP_ADULTS_T2DM") |
| name | String | Yes | No | Population name |
| description | String | Yes | No | Detailed population description |
| age_range | String | No | No | Age criteria (e.g., "≥18 years") |
| inclusion_criteria | List[String] | Yes | No | What defines this population |
| exclusion_criteria | List[String] | No | No | What excludes from this population |
| prevalence_description | String | No | No | How common is this population |
| guideline_id | String | Yes | No | Parent guideline reference |

**Constraints**:
```cypher
CREATE CONSTRAINT population_id_unique IF NOT EXISTS
FOR (pp:PatientPopulation) REQUIRE pp.population_id IS UNIQUE;
```

**Relationships**:
- `(PatientPopulation)-[:DEFINED_IN]->(KeyQuestion)` - PICOTS population
- `(PatientPopulation)-[:STUDIED_IN]->(Study)`
- `(PatientPopulation)-[:TARGETED_BY]->(Recommendation)`

**Example**:
```cypher
CREATE (pp:PatientPopulation {
  population_id: "POP_ADULTS_T2DM",
  name: "Adults with Type 2 Diabetes Mellitus",
  description: "Nonpregnant adults age ≥18 years with diagnosed T2DM in primary care settings",
  age_range: "≥18 years",
  inclusion_criteria: ["Diagnosed T2DM", "Age ≥18", "Non-pregnant", "Community-dwelling"],
  exclusion_criteria: ["Type 1 diabetes", "Gestational diabetes", "Pregnancy", "Exclusively managed in specialty care"],
  prevalence_description: "Approximately 10-12% of US adult population",
  guideline_id: "CPG_DM_2023"
})
```

---

### 14. PATIENT_CHARACTERISTIC

**Purpose**: Specific patient attribute that modifies treatment decisions (comorbidity, risk factor, etc.)

**Label**: `PatientCharacteristic`

**Properties**:
| Property | Type | Required | Unique | Description |
|----------|------|----------|--------|-------------|
| characteristic_id | String | Yes | Yes | Unique identifier (e.g., "PC_ASCVD") |
| name | String | Yes | No | Characteristic name |
| description | String | Yes | No | Detailed description |
| type | String | Yes | No | Enum: "Comorbidity", "Risk Factor", "Demographic", "Laboratory", "Functional Status" |
| prevalence_in_population | String | No | No | How common in target population |
| clinical_impact | String | No | No | Level of impact: "High", "Moderate", "Low" |
| modifies_treatment | Boolean | Yes | No | Does this change treatment approach? |
| measurement_method | String | No | No | How is this characteristic assessed? |

**Constraints**:
```cypher
CREATE CONSTRAINT characteristic_id_unique IF NOT EXISTS
FOR (pc:PatientCharacteristic) REQUIRE pc.characteristic_id IS UNIQUE;
```

**Relationships**:
- `(PatientCharacteristic)-[:MODIFIES {impact: String}]->(Recommendation)` - impact describes how (strengthens/weakens)
- `(PatientCharacteristic)-[:REQUIRES]->(ClinicalScenario)`
- `(PatientCharacteristic)-[:INCREASES_RISK_OF]->(AdverseEvent)`
- `(PatientCharacteristic)-[:PART_OF]->(PatientPopulation)`

**Example**:
```cypher
CREATE (pc:PatientCharacteristic {
  characteristic_id: "PC_ASCVD",
  name: "Established ASCVD",
  description: "History of atherosclerotic cardiovascular disease including MI, stroke, or peripheral arterial disease",
  type: "Comorbidity",
  prevalence_in_population: "32% of adults with T2DM",
  clinical_impact: "High",
  modifies_treatment: true,
  measurement_method: "Clinical history, documented prior CV event"
})
```

---

### 15. CONTRAINDICATION

**Purpose**: Warning or contraindication for an intervention

**Label**: `Contraindication`

**Properties**:
| Property | Type | Required | Unique | Description |
|----------|------|----------|--------|-------------|
| contraindication_id | String | Yes | Yes | Unique identifier (e.g., "CI_METFORMIN_RENAL") |
| type | String | Yes | No | Enum: "Absolute", "Relative", "Precaution" |
| condition | String | Yes | No | Condition that contraindicates |
| rationale | String | Yes | No | Why this is contraindicated |
| evidence_quality | String | No | No | Quality of supporting evidence |
| alternative_actions | String | No | No | What to do instead |
| severity | String | Yes | No | How serious: "Critical", "Important", "Minor" |

**Constraints**:
```cypher
CREATE CONSTRAINT contraindication_id_unique IF NOT EXISTS
FOR (ci:Contraindication) REQUIRE ci.contraindication_id IS UNIQUE;
```

**Relationships**:
- `(Contraindication)-[:CONTRAINDICATES]->(Intervention)`
- `(Contraindication)-[:APPLIES_TO]->(PatientCharacteristic)`
- `(Contraindication)-[:BASED_ON]->(EvidenceBody)`
- `(Contraindication)-[:OVERRIDES {context: String}]->(Recommendation)`

**Example**:
```cypher
CREATE (ci:Contraindication {
  contraindication_id: "CI_METFORMIN_RENAL",
  type: "Absolute",
  condition: "Severe renal impairment (eGFR <30 mL/min)",
  rationale: "Risk of lactic acidosis due to metformin accumulation",
  evidence_quality: "Moderate",
  alternative_actions: "Use alternative agent such as DPP-4 inhibitor; avoid metformin",
  severity: "Critical"
})
```

---

### 16. QUALITY_ASSESSMENT

**Purpose**: GRADE evaluation component for evidence quality

**Label**: `QualityAssessment`

**Properties**:
| Property | Type | Required | Unique | Description |
|----------|------|----------|--------|-------------|
| assessment_id | String | Yes | Yes | Unique identifier (e.g., "QA_001") |
| evidence_body_id | String | Yes | No | Evidence body being assessed |
| domain | String | Yes | No | GRADE domain: "Risk of Bias", "Consistency", "Directness", "Precision", "Publication Bias" |
| rating | String | Yes | No | Domain rating: "No serious issues", "Serious", "Very serious" |
| direction | String | Yes | No | "Downgrade", "Upgrade", "No change" |
| justification | String | Yes | No | Explanation for rating |
| assessor | String | No | No | Who performed assessment |
| assessment_date | Date | Yes | No | When assessed |

**Constraints**:
```cypher
CREATE CONSTRAINT assessment_id_unique IF NOT EXISTS
FOR (qa:QualityAssessment) REQUIRE qa.assessment_id IS UNIQUE;
```

**Relationships**:
- `(QualityAssessment)-[:EVALUATES]->(EvidenceBody)`
- `(QualityAssessment)-[:INFORMS]->(DecisionFramework)`

**Example**:
```cypher
CREATE (qa:QualityAssessment {
  assessment_id: "QA_001",
  evidence_body_id: "EVB_001",
  domain: "Risk of Bias",
  rating: "No serious issues",
  direction: "No change",
  justification: "All included RCTs rated Good quality by USPSTF criteria",
  assessor: "Evidence Review Team",
  assessment_date: date("2022-04-11")
})
```

---

### 17. DECISION_FRAMEWORK

**Purpose**: GRADE evidence-to-recommendation reasoning (4 domains)

**Label**: `DecisionFramework`

**Properties**:
| Property | Type | Required | Unique | Description |
|----------|------|----------|--------|-------------|
| framework_id | String | Yes | Yes | Unique identifier (e.g., "DF_001") |
| recommendation_id | String | Yes | No | Recommendation being determined |
| confidence_in_evidence | String | Yes | No | GRADE: "High", "Moderate", "Low", "Very Low" |
| balance_of_outcomes | String | Yes | No | Options: "Benefits outweigh harms", "Benefits slightly outweigh harms", "Balanced", "Harms slightly outweigh benefits", "Harms outweigh benefits" |
| patient_values | String | Yes | No | Description of patient values consideration |
| other_implications | String | Yes | No | Resource use, equity, acceptability, feasibility considerations |
| overall_judgment | String | Yes | No | Summary rationale for recommendation strength/direction |

**Constraints**:
```cypher
CREATE CONSTRAINT framework_id_unique IF NOT EXISTS
FOR (df:DecisionFramework) REQUIRE df.framework_id IS UNIQUE;
```

**Relationships**:
- `(DecisionFramework)-[:CONSIDERS]->(EvidenceBody)`
- `(DecisionFramework)-[:WEIGHS]->(Benefit)`
- `(DecisionFramework)-[:WEIGHS]->(AdverseEvent)`
- `(DecisionFramework)-[:DETERMINES]->(Recommendation)`
- `(DecisionFramework)-[:INFORMED_BY]->(QualityAssessment)`

**Example**:
```cypher
CREATE (df:DecisionFramework {
  framework_id: "DF_007",
  recommendation_id: "REC_007",
  confidence_in_evidence: "Moderate",
  balance_of_outcomes: "Benefits outweigh harms",
  patient_values: "Patients highly value education and empowerment; DSME addresses patient-expressed needs for understanding their disease and self-management",
  other_implications: "Resource considerations: DSME programs widely available in VA/DoD facilities. Equity: ensures all patients receive standardized education. High acceptability among patients and providers.",
  overall_judgment: "Strong For recommendation despite moderate evidence quality due to clear benefits, patient values alignment, and minimal harms"
})
```

---

## Relationship Types

### Evidence Chain Relationships

| Relationship | From | To | Properties | Description |
|--------------|------|-----|------------|-------------|
| INCLUDES | EvidenceBody | Study | None | Evidence body includes this study |
| SYNTHESIZES | EvidenceBody | Study | None | Evidence body synthesizes multiple studies |
| ANSWERS | EvidenceBody | KeyQuestion | None | Evidence body answers key question |
| SUPPORTS | EvidenceBody | Recommendation | strength: String | Evidence supports recommendation (with strength qualifier) |
| REFUTES | EvidenceBody | Recommendation | reason: String | Evidence argues against recommendation |
| EVALUATED_BY | EvidenceBody | QualityAssessment | None | Evidence quality assessed |
| MEASURES | Study | OutcomeMeasurement | None | Study measured this outcome |
| DEMONSTRATES | Study | Benefit/AdverseEvent | None | Study demonstrated this effect |

### Clinical Decision Relationships

| Relationship | From | To | Properties | Description |
|--------------|------|-----|------------|-------------|
| PART_OF | ClinicalModule | Guideline | None | Module is part of guideline |
| CONTAINS | ClinicalModule | KeyQuestion | None | Module contains key questions |
| ADDRESSES | KeyQuestion | ClinicalModule | None | Key question addresses module topic |
| LEADS_TO | KeyQuestion | Recommendation | None | Key question led to recommendation |
| TRIGGERS | ClinicalScenario | Recommendation | priority: Integer | Scenario triggers this recommendation (1=first line, 2=second line, etc.) |
| APPLIES_TO | Recommendation | PatientPopulation/ClinicalScenario | None | Recommendation applies to this group/scenario |
| REQUIRES | ClinicalScenario | PatientCharacteristic | None | Scenario requires this characteristic |

### Intervention Relationships

| Relationship | From | To | Properties | Description |
|--------------|------|-----|------------|-------------|
| RECOMMENDS | Recommendation | Intervention | preference: String | Recommendation suggests this intervention (optional: "preferred", "alternative") |
| COMPARES | Study | Intervention | vs: String, outcome: String | Study compared interventions |
| PRODUCES | Intervention | Benefit | magnitude: String | Intervention produces this benefit |
| CAUSES | Intervention | AdverseEvent | frequency: String | Intervention causes this adverse event |
| CONTRAINDICATED_BY | Intervention | Contraindication | None | Intervention has this contraindication |
| ALTERNATIVE_TO | Intervention | Intervention | context: String | Interventions are alternatives |
| COMBINES_WITH | Intervention | Intervention | None | Interventions can be combined |

### Modification Relationships

| Relationship | From | To | Properties | Description |
|--------------|------|-----|------------|-------------|
| MODIFIES | PatientCharacteristic | Recommendation | impact: String, direction: String | Characteristic modifies recommendation (impact: "strengthens"/"weakens", direction: "for"/"against") |
| CONTRAINDICATES | Contraindication | Intervention | None | Contraindication prevents intervention use |
| OVERRIDES | Contraindication | Recommendation | context: String | Contraindication overrides recommendation in certain contexts |
| INCREASES_RISK_OF | PatientCharacteristic | AdverseEvent | magnitude: String | Characteristic increases AE risk |

### Reasoning Relationships

| Relationship | From | To | Properties | Description |
|--------------|------|-----|------------|-------------|
| CONSIDERS | DecisionFramework | EvidenceBody | None | Framework considers this evidence |
| WEIGHS | DecisionFramework | Benefit/AdverseEvent | weight: String | Framework weighs this outcome (weight: "critical", "important") |
| DETERMINES | DecisionFramework | Recommendation | None | Framework determined recommendation strength/direction |
| INFORMED_BY | DecisionFramework | QualityAssessment | None | Framework informed by quality assessment |
| INFORMS | QualityAssessment | DecisionFramework | None | Assessment informs decision framework |

### Versioning Relationships

| Relationship | From | To | Properties | Description |
|--------------|------|-----|------------|-------------|
| SUPERSEDES | Recommendation (new) | Recommendation (old) | reason: String, date: Date | New recommendation replaces old |
| VERSION_OF | Any entity | Version metadata | version_number: String | Entity version tracking |
| UPDATES | Study (new) | EvidenceBody | date: Date | New study triggers evidence review |
| REPLACES | Any entity | Previous version | None | General versioning relationship |

---

## Compound Indexes

For performance optimization on common query patterns:

```cypher
-- Guideline + version lookups
CREATE INDEX guideline_version IF NOT EXISTS
FOR (g:Guideline) ON (g.guideline_id, g.version);

-- Recommendation filtering
CREATE INDEX rec_strength_direction IF NOT EXISTS
FOR (r:Recommendation) ON (r.strength, r.direction);

-- Study searches
CREATE INDEX study_year_type IF NOT EXISTS
FOR (s:Study) ON (s.year, s.study_type);

-- Intervention queries
CREATE INDEX intervention_class_type IF NOT EXISTS
FOR (i:Intervention) ON (i.drug_class, i.type);
```

---

## Vector Indexes

For semantic similarity search on text properties:

```cypher
-- Recommendation text similarity
CREATE VECTOR INDEX recommendation_embedding IF NOT EXISTS
FOR (r:Recommendation) ON (r.embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 1536,
  `vector.similarity_function`: 'cosine'
}};

-- Clinical scenario similarity
CREATE VECTOR INDEX scenario_embedding IF NOT EXISTS
FOR (cs:ClinicalScenario) ON (cs.embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 1536,
  `vector.similarity_function`: 'cosine'
}};

-- Intervention description similarity
CREATE VECTOR INDEX intervention_embedding IF NOT EXISTS
FOR (i:Intervention) ON (i.embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 1536,
  `vector.similarity_function`: 'cosine'
}};
```

**Note**: Embeddings are generated separately and stored as Float array properties. See `docs/technical/VECTOR_SEARCH.md` for details.

---

## Schema Validation Queries

Use these queries to verify schema integrity:

```cypher
-- List all constraints
SHOW CONSTRAINTS;

-- List all indexes
SHOW INDEXES;

-- Count nodes by label
MATCH (n)
RETURN labels(n)[0] as NodeType, count(*) as Count
ORDER BY Count DESC;

-- Count relationships by type
MATCH ()-[r]->()
RETURN type(r) as RelationshipType, count(*) as Count
ORDER BY Count DESC;

-- Verify required properties exist
MATCH (r:Recommendation)
WHERE r.rec_id IS NULL OR r.rec_text IS NULL OR r.strength IS NULL
RETURN count(*) as MissingRequiredProps;
```

---

## Design Notes

### Why Separate Benefit and AdverseEvent?
Rather than generic "Outcome" nodes with a valence property, separating benefits and harms as first-class entities:
- Makes benefit-harm balance queries explicit and natural
- Mirrors clinical thinking (clinicians think in terms of benefits vs risks)
- Enables relationship traversal like "show all adverse events caused by this intervention"
- Supports GRADE decision framework which explicitly weighs benefits against harms

### Why OutcomeMeasurement in Addition to Outcome?
- **Outcome**: General concept (e.g., "HbA1c") - reusable across studies
- **OutcomeMeasurement**: Specific measured value in a specific study (e.g., "-1.5% at 30 weeks")
- Allows aggregating across studies at the Outcome level while preserving study-specific detail

### Versioning Strategy
- Primary entities (Recommendation, EvidenceBody, Guideline) include version properties
- SUPERSEDES relationships create version chains
- Status property tracks lifecycle ("Active", "Superseded", "Under Review")
- Enables temporal queries ("what was recommended in version 5.0?")

### Multi-Disease Extension
- Guideline node contains disease-specific guidelines
- All other nodes reference guideline_id for scoping
- Shared entities (e.g., common interventions like metformin) can link to multiple guidelines
- Schema structure is disease-agnostic

---

**Document Version**: 1.0  
**Last Updated**: February 4, 2026  
**Next Review**: After implementation validation
