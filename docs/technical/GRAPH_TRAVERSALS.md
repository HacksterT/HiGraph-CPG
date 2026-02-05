# HiGraph-CPG Graph Traversal Patterns

## Overview

This document provides example Cypher queries demonstrating how to traverse the HiGraph-CPG knowledge graph to answer clinical questions. Each pattern includes the query, expected use case, example output, and performance considerations.

**Document Version**: 1.0  
**Database**: Neo4j 5.x  
**Last Updated**: February 4, 2026

---

## Query Categories

1. [Evidence Chain Traversals](#evidence-chain-traversals) - From studies to recommendations
2. [Clinical Decision Support](#clinical-decision-support) - Point-of-care queries
3. [Benefit-Harm Analysis](#benefit-harm-analysis) - Risk-benefit evaluation
4. [Contraindication Checking](#contraindication-checking) - Safety queries
5. [Versioning & History](#versioning--history) - Temporal queries
6. [Semantic Search](#semantic-search) - Vector similarity queries
7. [Complex Multi-Hop](#complex-multi-hop) - Advanced traversals

---

## Evidence Chain Traversals

### Pattern 1: Recommendation → Evidence → Studies

**Clinical Question**: "What evidence supports the recommendation to use metformin?"

**Query**:
```cypher
MATCH (r:Recommendation {rec_id: 'REC_008'})
-[:BASED_ON]->(eb:EvidenceBody)
-[:INCLUDES]->(s:Study)
RETURN 
  r.rec_text as Recommendation,
  r.strength as Strength,
  eb.topic as EvidenceTopic,
  eb.quality_rating as Quality,
  collect({
    title: s.title,
    year: s.year,
    pmid: s.pmid,
    study_type: s.study_type,
    quality: s.study_quality
  }) as SupportingStudies
```

**Expected Output**:
```json
{
  "Recommendation": "In adults with newly diagnosed T2DM, we recommend metformin as first-line pharmacotherapy",
  "Strength": "Strong",
  "EvidenceTopic": "Metformin efficacy and safety",
  "Quality": "High",
  "SupportingStudies": [
    {
      "title": "Effect of intensive blood-glucose control with metformin...",
      "year": 1998,
      "pmid": "9742976",
      "study_type": "RCT",
      "quality": "Good"
    },
    // ... more studies
  ]
}
```

**Use Case**: Clinician wants to see the evidence base supporting a recommendation  
**Performance**: Fast (<50ms) with indexes on rec_id and BASED_ON relationship

---

### Pattern 2: Study → Outcomes → Measurements

**Clinical Question**: "What outcomes were measured in the UKPDS 34 trial?"

**Query**:
```cypher
MATCH (s:Study {study_id: 'STUDY_UKPDS34'})
-[:MEASURES]->(om:OutcomeMeasurement)
-[:MEASURES]->(o:Outcome)
RETURN 
  s.title as StudyTitle,
  collect(DISTINCT {
    outcome: o.name,
    criticality: o.criticality,
    value: om.value,
    timeframe: om.timeframe,
    significance: om.statistical_significance
  }) as Outcomes
ORDER BY o.criticality DESC
```

**Expected Output**:
```json
{
  "StudyTitle": "Effect of intensive blood-glucose control with metformin...",
  "Outcomes": [
    {
      "outcome": "Diabetes-related mortality",
      "criticality": "Critical",
      "value": "42% reduction",
      "timeframe": "10 years",
      "significance": "p=0.017"
    },
    {
      "outcome": "HbA1c",
      "criticality": "Critical",
      "value": "-1.5%",
      "timeframe": "10 years",
      "significance": "p<0.001"
    }
  ]
}
```

**Use Case**: Detailed study analysis, evidence synthesis  
**Performance**: Fast with study_id index

---

### Pattern 3: Key Question → Evidence → Recommendations

**Clinical Question**: "What recommendations came from Key Question 5 about pharmacotherapy?"

**Query**:
```cypher
MATCH (kq:KeyQuestion {kq_number: 5})
-[:ANSWERED_BY]->(eb:EvidenceBody)
-[:SUPPORTS]->(r:Recommendation)
RETURN 
  kq.question_text as KeyQuestion,
  collect({
    recommendation: r.rec_text,
    strength: r.strength,
    direction: r.direction,
    evidence_quality: eb.quality_rating,
    num_studies: eb.num_studies
  }) as Recommendations
ORDER BY r.rec_number
```

**Expected Output**: List of recommendations with their evidence strength

**Use Case**: Understanding how systematic review questions led to clinical recommendations  
**Performance**: Fast (<100ms)

---

## Clinical Decision Support

### Pattern 4: Clinical Scenario → Applicable Recommendations

**Clinical Question**: "What should I prescribe for a newly diagnosed T2DM patient?"

**Query**:
```cypher
MATCH (cs:ClinicalScenario {scenario_id: 'CS_NEWDX_T2DM'})
-[t:TRIGGERS]->(r:Recommendation)
WHERE r.status = 'Active'
RETURN 
  cs.name as Scenario,
  cs.description as Description,
  collect({
    rec_number: r.rec_number,
    recommendation: r.rec_text,
    strength: r.strength,
    priority: t.priority,
    category: r.topic
  }) as Recommendations
ORDER BY t.priority, r.rec_number
```

**Expected Output**:
```json
{
  "Scenario": "Newly diagnosed T2DM, no complications",
  "Description": "Adult patient with recent T2DM diagnosis...",
  "Recommendations": [
    {
      "rec_number": 7,
      "recommendation": "We recommend diabetes self-management education",
      "strength": "Strong",
      "priority": 1,
      "category": "Self-Management"
    },
    {
      "rec_number": 8,
      "recommendation": "We recommend lifestyle modification plus metformin",
      "strength": "Strong",
      "priority": 1,
      "category": "Pharmacotherapy"
    }
  ]
}
```

**Use Case**: Point-of-care decision support at patient encounter  
**Performance**: Very fast (<50ms) - critical for clinical use

---

### Pattern 5: Patient Characteristics → Modified Recommendations

**Clinical Question**: "How does the presence of ASCVD change treatment recommendations?"

**Query**:
```cypher
MATCH (pc:PatientCharacteristic {characteristic_id: 'PC_ASCVD'})
-[m:MODIFIES]->(r:Recommendation)
-[:RECOMMENDS]->(i:Intervention)
WHERE r.status = 'Active'
RETURN 
  pc.name as Characteristic,
  pc.prevalence_in_population as Prevalence,
  collect({
    recommendation: r.rec_text,
    modification_impact: m.impact,
    modification_direction: m.direction,
    preferred_interventions: collect(DISTINCT i.name)
  }) as ModifiedRecommendations
```

**Expected Output**:
```json
{
  "Characteristic": "Established ASCVD",
  "Prevalence": "32% of adults with T2DM",
  "ModifiedRecommendations": [
    {
      "recommendation": "In T2DM with ASCVD, prefer agents with proven CV benefit",
      "modification_impact": "strengthens",
      "modification_direction": "for",
      "preferred_interventions": ["GLP-1 RA", "SGLT-2 inhibitor"]
    }
  ]
}
```

**Use Case**: Personalized treatment based on patient comorbidities  
**Performance**: Fast (<100ms)

---

### Pattern 6: Intervention → All Related Information

**Clinical Question**: "Tell me everything about SGLT-2 inhibitors for this patient"

**Query**:
```cypher
MATCH (i:Intervention {intervention_id: 'INT_SGLT2I'})
OPTIONAL MATCH (i)-[:PRODUCES]->(b:Benefit)
OPTIONAL MATCH (i)-[:CAUSES]->(ae:AdverseEvent)
OPTIONAL MATCH (ci:Contraindication)-[:CONTRAINDICATES]->(i)
OPTIONAL MATCH (r:Recommendation)-[:RECOMMENDS]->(i)
WHERE r.status = 'Active'
RETURN 
  i.name as Intervention,
  i.drug_class as DrugClass,
  i.mechanism as Mechanism,
  i.typical_dose as Dosing,
  collect(DISTINCT {
    benefit: b.name,
    magnitude: b.magnitude,
    confidence: b.confidence
  }) as Benefits,
  collect(DISTINCT {
    adverse_event: ae.name,
    severity: ae.severity,
    frequency: ae.frequency
  }) as AdverseEvents,
  collect(DISTINCT {
    contraindication: ci.condition,
    type: ci.type,
    severity: ci.severity
  }) as Contraindications,
  collect(DISTINCT {
    recommendation: r.rec_text,
    strength: r.strength
  }) as Recommendations
```

**Expected Output**: Comprehensive intervention profile with benefits, risks, contraindications

**Use Case**: Quick reference during prescribing decision  
**Performance**: Moderate (<200ms) due to multiple OPTIONAL MATCH patterns

---

## Benefit-Harm Analysis

### Pattern 7: Intervention → Benefit-Harm Balance

**Clinical Question**: "What are the benefits and risks of metformin?"

**Query**:
```cypher
MATCH (i:Intervention {name: 'Metformin'})
OPTIONAL MATCH (i)-[:PRODUCES]->(b:Benefit)
-[:DEMONSTRATED_IN]->(s1:Study)
OPTIONAL MATCH (i)-[:CAUSES]->(ae:AdverseEvent)
-[:DEMONSTRATED_IN]->(s2:Study)
WITH i, 
  collect(DISTINCT {
    benefit: b.name,
    magnitude: b.magnitude,
    criticality: b.criticality,
    num_studies: count(DISTINCT s1)
  }) as Benefits,
  collect(DISTINCT {
    adverse_event: ae.name,
    severity: ae.severity,
    frequency: ae.frequency,
    criticality: ae.criticality,
    num_studies: count(DISTINCT s2)
  }) as AdverseEvents
RETURN 
  i.name as Intervention,
  Benefits,
  AdverseEvents,
  size([b IN Benefits WHERE b.criticality = 'Critical']) as CriticalBenefits,
  size([ae IN AdverseEvents WHERE ae.criticality = 'Critical']) as CriticalHarms
```

**Expected Output**:
```json
{
  "Intervention": "Metformin",
  "Benefits": [
    {
      "benefit": "HbA1c reduction",
      "magnitude": "1.5%",
      "criticality": "Critical",
      "num_studies": 12
    },
    {
      "benefit": "Weight neutral or loss",
      "magnitude": "0-2 kg loss",
      "criticality": "Important",
      "num_studies": 8
    }
  ],
  "AdverseEvents": [
    {
      "adverse_event": "GI side effects",
      "severity": "Mild to Moderate",
      "frequency": "20-30%",
      "criticality": "Important",
      "num_studies": 15
    },
    {
      "adverse_event": "Lactic acidosis",
      "severity": "Life-threatening",
      "frequency": "Rare",
      "criticality": "Critical",
      "num_studies": 3
    }
  ],
  "CriticalBenefits": 1,
  "CriticalHarms": 1
}
```

**Use Case**: Shared decision-making, patient counseling  
**Performance**: Moderate (<200ms)

---

### Pattern 8: Decision Framework → GRADE Reasoning

**Clinical Question**: "Why is this recommendation Strong For despite moderate evidence?"

**Query**:
```cypher
MATCH (r:Recommendation {rec_id: 'REC_007'})
<-[:DETERMINES]-(df:DecisionFramework)
-[:CONSIDERS]->(eb:EvidenceBody)
OPTIONAL MATCH (df)-[:WEIGHS]->(b:Benefit)
OPTIONAL MATCH (df)-[:WEIGHS]->(ae:AdverseEvent)
RETURN 
  r.rec_text as Recommendation,
  r.strength as Strength,
  df.confidence_in_evidence as EvidenceQuality,
  df.balance_of_outcomes as BenefitHarmBalance,
  df.patient_values as PatientValues,
  df.other_implications as OtherConsiderations,
  df.overall_judgment as Rationale,
  collect(DISTINCT b.name) as BenefitsConsidered,
  collect(DISTINCT ae.name) as HarmsConsidered
```

**Expected Output**: Complete GRADE reasoning chain explaining recommendation strength

**Use Case**: Understanding guideline development process, teaching  
**Performance**: Fast (<100ms)

---

## Contraindication Checking

### Pattern 9: Patient Characteristic → Contraindicated Interventions

**Clinical Question**: "What medications should I avoid in a patient with eGFR <30?"

**Query**:
```cypher
MATCH (pc:PatientCharacteristic)
WHERE pc.name CONTAINS 'renal' AND pc.description CONTAINS 'eGFR <30'
MATCH (ci:Contraindication)-[:APPLIES_TO]->(pc)
MATCH (ci)-[:CONTRAINDICATES]->(i:Intervention)
RETURN 
  pc.name as PatientCondition,
  collect({
    intervention: i.name,
    contraindication_type: ci.type,
    rationale: ci.rationale,
    severity: ci.severity,
    alternatives: ci.alternative_actions
  }) as ContraindicatedMedications
ORDER BY ci.severity DESC
```

**Expected Output**:
```json
{
  "PatientCondition": "Severe renal impairment (eGFR <30)",
  "ContraindicatedMedications": [
    {
      "intervention": "Metformin",
      "contraindication_type": "Absolute",
      "rationale": "Risk of lactic acidosis due to accumulation",
      "severity": "Critical",
      "alternatives": "Use DPP-4 inhibitor or insulin"
    },
    {
      "intervention": "SGLT-2 inhibitor",
      "contraindication_type": "Relative",
      "rationale": "Reduced efficacy in severe renal impairment",
      "severity": "Important",
      "alternatives": "Consider GLP-1 RA or insulin"
    }
  ]
}
```

**Use Case**: Safety checking before prescribing, clinical decision support alerts  
**Performance**: Fast (<50ms) - critical for safety

---

### Pattern 10: Intervention + Multiple Characteristics → Safety Check

**Clinical Question**: "Is this medication safe for this specific patient?"

**Query**:
```cypher
// Patient characteristics
WITH ['PC_RENAL_SEVERE', 'PC_HF', 'PC_ELDERLY'] as patientChars
MATCH (i:Intervention {intervention_id: 'INT_METFORMIN'})
OPTIONAL MATCH (ci:Contraindication)-[:CONTRAINDICATES]->(i)
OPTIONAL MATCH (ci)-[:APPLIES_TO]->(pc:PatientCharacteristic)
WHERE pc.characteristic_id IN patientChars
OPTIONAL MATCH (ae:AdverseEvent)<-[:CAUSES]-(i)
OPTIONAL MATCH (ae)<-[:INCREASES_RISK_OF]-(pc2:PatientCharacteristic)
WHERE pc2.characteristic_id IN patientChars
RETURN 
  i.name as Medication,
  collect(DISTINCT {
    contraindication: ci.condition,
    type: ci.type,
    severity: ci.severity,
    applies_to: pc.name
  }) as Contraindications,
  collect(DISTINCT {
    adverse_event: ae.name,
    baseline_risk: ae.frequency,
    increased_by: pc2.name
  }) as IncreasedRisks,
  CASE 
    WHEN size(collect(DISTINCT ci)) = 0 THEN 'SAFE'
    WHEN ANY(c IN collect(ci) WHERE c.type = 'Absolute') THEN 'CONTRAINDICATED'
    ELSE 'USE WITH CAUTION'
  END as SafetyAssessment
```

**Expected Output**: Safety assessment with specific contraindications and increased risks

**Use Case**: Automated safety screening in EHR integration  
**Performance**: Fast (<100ms)

---

## Versioning & History

### Pattern 11: Recommendation Version History

**Clinical Question**: "How has the metformin recommendation changed over time?"

**Query**:
```cypher
MATCH path = (current:Recommendation {rec_number: 8, status: 'Active'})
-[:SUPERSEDES*0..]->(historical:Recommendation)
WHERE historical.rec_number = 8
RETURN 
  [r IN nodes(path) | {
    version: r.version,
    date: r.version_date,
    text: r.rec_text,
    strength: r.strength,
    direction: r.direction,
    category: r.category,
    status: r.status
  }] as VersionHistory
ORDER BY historical.version_date DESC
```

**Expected Output**: Chronological list of recommendation versions showing evolution

**Use Case**: Guideline development, understanding changes, quality improvement  
**Performance**: Fast (<100ms)

---

### Pattern 12: Evidence Updates Triggering Reviews

**Clinical Question**: "What new studies since 2022 might require recommendation updates?"

**Query**:
```cypher
MATCH (s:Study)
WHERE s.year >= 2022
MATCH (s)-[:INCLUDED_IN]->(eb:EvidenceBody)
-[:SUPPORTS]->(r:Recommendation)
WHERE r.status = 'Active' AND r.version_date < date('2022-01-01')
RETURN 
  r.rec_id as RecommendationID,
  r.rec_text as Recommendation,
  r.version_date as LastUpdated,
  collect({
    study: s.title,
    year: s.year,
    pmid: s.pmid,
    study_type: s.study_type
  }) as NewEvidenceSince2022,
  count(s) as NumNewStudies
HAVING count(s) > 0
ORDER BY count(s) DESC
```

**Expected Output**: Recommendations that may need updating based on new evidence

**Use Case**: Automated evidence monitoring, guideline maintenance  
**Performance**: Moderate (<500ms) for large evidence bases

---

## Semantic Search

### Pattern 13: Find Similar Recommendations

**Clinical Question**: "Find recommendations similar to 'lifestyle modification'"

**Query**:
```cypher
// First, get embedding for query text (done in application layer)
// Assume query_embedding is the vector for "lifestyle modification"

CALL db.index.vector.queryNodes(
  'recommendation_embedding', 
  10, 
  $query_embedding
) YIELD node AS r, score
RETURN 
  r.rec_text as Recommendation,
  r.strength as Strength,
  r.topic as Topic,
  score as SimilarityScore
ORDER BY score DESC
LIMIT 5
```

**Parameters**:
```json
{
  "query_embedding": [0.123, -0.456, 0.789, ...] // 1536-dimension vector
}
```

**Expected Output**: Top 5 semantically similar recommendations with similarity scores

**Use Case**: Natural language query interface, chatbot search  
**Performance**: Very fast (<50ms) with vector index

---

### Pattern 14: Find Interventions by Clinical Concept

**Clinical Question**: "What medications help with cardiovascular protection?"

**Query**:
```cypher
// Get embedding for "cardiovascular protection"
CALL db.index.vector.queryNodes(
  'intervention_embedding',
  20,
  $concept_embedding
) YIELD node AS i, score
MATCH (i)-[:PRODUCES]->(b:Benefit)
WHERE b.name CONTAINS 'cardiovascular' OR b.name CONTAINS 'CV'
RETURN DISTINCT
  i.name as Intervention,
  i.drug_class as Class,
  collect(b.name) as CVBenefits,
  score as RelevanceScore
ORDER BY score DESC
LIMIT 10
```

**Expected Output**: Interventions with CV benefits ranked by semantic relevance

**Use Case**: Exploratory search, finding relevant therapies by concept  
**Performance**: Fast (<100ms)

---

## Complex Multi-Hop

### Pattern 15: Complete Clinical Picture

**Clinical Question**: "Give me everything relevant for a T2DM patient with CKD and heart failure"

**Query**:
```cypher
// Define patient characteristics
WITH ['PC_CKD_STAGE4', 'PC_HF_REDUCED_EF'] as patientChars

// Find applicable scenarios
MATCH (cs:ClinicalScenario)-[:REQUIRES]->(pc:PatientCharacteristic)
WHERE pc.characteristic_id IN patientChars
WITH cs, patientChars

// Get triggered recommendations
MATCH (cs)-[:TRIGGERS]->(r:Recommendation)
WHERE r.status = 'Active'

// Get recommended interventions
MATCH (r)-[:RECOMMENDS]->(i:Intervention)

// Check contraindications
OPTIONAL MATCH (ci:Contraindication)-[:CONTRAINDICATES]->(i)
OPTIONAL MATCH (ci)-[:APPLIES_TO]->(pc2:PatientCharacteristic)
WHERE pc2.characteristic_id IN patientChars

// Get benefits specific to patient characteristics
OPTIONAL MATCH (i)-[:PRODUCES]->(b:Benefit)
WHERE b.name CONTAINS 'renal' OR b.name CONTAINS 'heart failure' OR b.name CONTAINS 'cardiovascular'

// Get adverse events with increased risk
OPTIONAL MATCH (i)-[:CAUSES]->(ae:AdverseEvent)
<-[:INCREASES_RISK_OF]-(pc3:PatientCharacteristic)
WHERE pc3.characteristic_id IN patientChars

RETURN 
  cs.name as ClinicalScenario,
  collect(DISTINCT {
    recommendation: r.rec_text,
    strength: r.strength,
    intervention: i.name,
    contraindicated: ci IS NOT NULL,
    contraindication_details: CASE 
      WHEN ci IS NOT NULL THEN {
        type: ci.type,
        condition: ci.condition,
        severity: ci.severity
      }
      ELSE null
    END,
    relevant_benefits: collect(DISTINCT b.name),
    increased_risks: collect(DISTINCT ae.name)
  }) as ClinicalGuidance
```

**Expected Output**: Comprehensive guidance including recommendations, contraindications, benefits, and risks

**Use Case**: Complex patient case review, comprehensive decision support  
**Performance**: Slower (<1s) due to complexity - use caching for repeated queries

---

### Pattern 16: Cross-Guideline Interactions

**Clinical Question**: "Does this patient's COPD guideline conflict with diabetes recommendations?"

**Query**:
```cypher
// Assuming we have multiple guidelines
MATCH (g1:Guideline {disease_condition: 'Type 2 Diabetes Mellitus'})
-[:CONTAINS_MODULE]->(m1:ClinicalModule)
-[:CONTAINS]->(r1:Recommendation)
-[:RECOMMENDS]->(i:Intervention)

MATCH (g2:Guideline {disease_condition: 'COPD'})
-[:CONTAINS_MODULE]->(m2:ClinicalModule)
-[:CONTAINS]->(r2:Recommendation)

// Look for explicit conflicts
OPTIONAL MATCH (r1)-[conf:CONFLICTS_WITH]->(r2)

// Look for contraindications
OPTIONAL MATCH (ci:Contraindication)-[:CONTRAINDICATES]->(i)
WHERE ci.condition CONTAINS 'COPD' OR ci.condition CONTAINS 'respiratory'

RETURN 
  r1.rec_text as DiabetesRecommendation,
  r2.rec_text as COPDRecommendation,
  i.name as Intervention,
  conf IS NOT NULL as HasExplicitConflict,
  collect(ci.condition) as Contraindications,
  CASE 
    WHEN conf IS NOT NULL OR size(collect(ci)) > 0 THEN 'CONFLICT'
    ELSE 'COMPATIBLE'
  END as InteractionStatus
```

**Expected Output**: Identification of conflicting recommendations across guidelines

**Use Case**: Multi-morbidity management, complex case coordination  
**Performance**: Moderate to slow depending on number of guidelines

---

## Performance Optimization Tips

### Index Usage
```cypher
// Always use indexed properties in WHERE clauses
MATCH (r:Recommendation)
WHERE r.rec_id = 'REC_001'  // Uses index
RETURN r

// Avoid string operations that prevent index usage
MATCH (r:Recommendation)
WHERE r.rec_id CONTAINS 'REC'  // Doesn't use index efficiently
RETURN r
```

### Limit Early
```cypher
// Good - limit early in traversal
MATCH (r:Recommendation)
WHERE r.status = 'Active'
WITH r LIMIT 10
MATCH (r)-[:BASED_ON]->(eb:EvidenceBody)
RETURN r, eb

// Bad - limit after expensive traversal
MATCH (r:Recommendation)-[:BASED_ON]->(eb:EvidenceBody)
WHERE r.status = 'Active'
RETURN r, eb
LIMIT 10
```

### Reduce Cardinality
```cypher
// Good - filter before expanding
MATCH (i:Intervention {intervention_id: 'INT_METFORMIN'})
MATCH (i)-[:PRODUCES]->(b:Benefit)
WHERE b.criticality = 'Critical'
RETURN i, collect(b)

// Bad - expand then filter
MATCH (i:Intervention {intervention_id: 'INT_METFORMIN'})
-[:PRODUCES]->(b:Benefit)
WHERE b.criticality = 'Critical'
RETURN i, collect(b)
```

### Use OPTIONAL MATCH Wisely
```cypher
// Good - OPTIONAL for truly optional relationships
MATCH (i:Intervention {name: 'Metformin'})
OPTIONAL MATCH (i)-[:CAUSES]->(ae:AdverseEvent)
RETURN i, collect(ae)

// Bad - OPTIONAL when relationship should exist
MATCH (r:Recommendation)
OPTIONAL MATCH (r)-[:BASED_ON]->(eb:EvidenceBody)  // Should always exist
RETURN r, eb
```

---

## Query Templates for Common Use Cases

### Template 1: Chatbot Query Handler
```cypher
// Generic query for chatbot: "Tell me about [intervention]"
MATCH (i:Intervention)
WHERE toLower(i.name) CONTAINS toLower($search_term)
  OR toLower(i.generic_name) CONTAINS toLower($search_term)
OPTIONAL MATCH (r:Recommendation)-[:RECOMMENDS]->(i)
WHERE r.status = 'Active'
OPTIONAL MATCH (i)-[:PRODUCES]->(b:Benefit)
WHERE b.criticality IN ['Critical', 'Important']
OPTIONAL MATCH (i)-[:CAUSES]->(ae:AdverseEvent)
WHERE ae.criticality IN ['Critical', 'Important']
OPTIONAL MATCH (ci:Contraindication)-[:CONTRAINDICATES]->(i)
WHERE ci.severity IN ['Critical', 'Important']
RETURN 
  i as Intervention,
  collect(DISTINCT r) as Recommendations,
  collect(DISTINCT b) as KeyBenefits,
  collect(DISTINCT ae) as KeyRisks,
  collect(DISTINCT ci) as Contraindications
LIMIT 1
```

### Template 2: Safety Alert
```cypher
// Check if intervention is safe given patient characteristics
MATCH (i:Intervention {intervention_id: $intervention_id})
OPTIONAL MATCH (ci:Contraindication)-[:CONTRAINDICATES]->(i)
OPTIONAL MATCH (ci)-[:APPLIES_TO]->(pc:PatientCharacteristic)
WHERE pc.characteristic_id IN $patient_characteristics
RETURN 
  size(collect(DISTINCT ci)) > 0 as HasContraindication,
  collect({
    condition: ci.condition,
    type: ci.type,
    severity: ci.severity
  }) as ContraindicationDetails
```

### Template 3: Personalized Recommendations
```cypher
// Get recommendations modified by patient characteristics
MATCH (cs:ClinicalScenario {scenario_id: $scenario_id})
-[:TRIGGERS]->(r:Recommendation)
WHERE r.status = 'Active'
OPTIONAL MATCH (pc:PatientCharacteristic)
-[m:MODIFIES]->(r)
WHERE pc.characteristic_id IN $patient_characteristics
RETURN 
  r.rec_text as Recommendation,
  r.strength as BaseStrength,
  collect({
    characteristic: pc.name,
    modifies_how: m.impact,
    modifies_direction: m.direction
  }) as PersonalizationFactors,
  CASE
    WHEN ANY(mod IN collect(m) WHERE mod.impact = 'strengthens' AND mod.direction = 'for')
      THEN 'STRONGLY RECOMMENDED'
    WHEN ANY(mod IN collect(m) WHERE mod.impact = 'weakens' AND mod.direction = 'against')
      THEN 'CONSIDER ALTERNATIVES'
    ELSE r.strength
  END as PersonalizedStrength
ORDER BY r.rec_number
```

---

## Testing Traversals

Use these queries to validate graph structure:

```cypher
// Check for orphaned recommendations (no evidence)
MATCH (r:Recommendation)
WHERE NOT (r)-[:BASED_ON]->(:EvidenceBody)
RETURN count(r) as OrphanedRecommendations

// Check for broken evidence chains
MATCH (eb:EvidenceBody)
WHERE NOT (eb)-[:INCLUDES]->(:Study)
RETURN count(eb) as EvidenceBodiesWithoutStudies

// Verify all active recommendations have decision frameworks
MATCH (r:Recommendation {status: 'Active'})
WHERE NOT (r)<-[:DETERMINES]-(:DecisionFramework)
RETURN count(r) as RecommendationsWithoutFramework

// Check relationship symmetry
MATCH (a)-[r:SUPERSEDES]->(b)
WHERE NOT (b)-[:SUPERSEDED_BY]->(a)
RETURN count(*) as AsymmetricVersioning
```

---

**Document Version**: 1.0  
**Last Updated**: February 4, 2026  
**Next Review**: After implementation and performance testing
