// ============================================================
// HiGraph-CPG Example Traversal Patterns
// ============================================================
// Each query demonstrates a clinical use case for the knowledge graph.
// Run these against seeded test data (see seed_test_data.cypher).

// ============================================================
// TRAVERSAL 1: Evidence Chain
// Clinical Question: "What evidence supports the metformin recommendation?"
// Pattern: Recommendation -> EvidenceBody -> Studies
// ============================================================

MATCH (r:Recommendation {rec_id: 'REC_008'})
-[:BASED_ON]->(eb:EvidenceBody)
-[:INCLUDES]->(s:Study)
RETURN
  r.rec_text AS Recommendation,
  r.strength AS Strength,
  eb.topic AS EvidenceTopic,
  eb.quality_rating AS EvidenceQuality,
  collect({
    title: s.title,
    year: s.year,
    pmid: s.pmid,
    study_type: s.study_type,
    quality: s.study_quality
  }) AS SupportingStudies;

// ============================================================
// TRAVERSAL 2: Clinical Decision Support
// Clinical Question: "What should I do for a newly diagnosed T2DM patient?"
// Pattern: ClinicalScenario -> Recommendations -> Interventions
// ============================================================

MATCH (cs:ClinicalScenario {scenario_id: 'CS_NEWDX_T2DM'})
-[t:TRIGGERS]->(r:Recommendation)
-[:RECOMMENDS]->(i:Intervention)
WHERE r.status = 'Active'
WITH cs, r, t, collect(i.name) AS Interventions
RETURN
  cs.name AS Scenario,
  r.rec_text AS Recommendation,
  r.strength AS Strength,
  t.priority AS Priority,
  Interventions
ORDER BY t.priority, r.rec_number;

// ============================================================
// TRAVERSAL 3: Benefit-Harm Analysis
// Clinical Question: "What are the benefits and risks of metformin?"
// Pattern: Intervention -> Benefits + AdverseEvents
// ============================================================

MATCH (i:Intervention {intervention_id: 'INT_METFORMIN'})
OPTIONAL MATCH (i)-[:PRODUCES]->(b:Benefit)
OPTIONAL MATCH (i)-[:CAUSES]->(ae:AdverseEvent)
RETURN
  i.name AS Intervention,
  collect(DISTINCT {
    benefit: b.name,
    magnitude: b.magnitude,
    criticality: b.criticality,
    confidence: b.confidence
  }) AS Benefits,
  collect(DISTINCT {
    adverse_event: ae.name,
    severity: ae.severity,
    frequency: ae.frequency,
    criticality: ae.criticality
  }) AS AdverseEvents;

// ============================================================
// TRAVERSAL 4: Contraindication Check
// Clinical Question: "What medications should I avoid in severe renal impairment?"
// Pattern: PatientCharacteristic -> Contraindication -> Intervention
// ============================================================

MATCH (pc:PatientCharacteristic {characteristic_id: 'PC_RENAL_SEVERE'})
<-[:APPLIES_TO]-(ci:Contraindication)
-[:CONTRAINDICATES]->(i:Intervention)
RETURN
  pc.name AS PatientCondition,
  collect({
    intervention: i.name,
    contraindication_type: ci.type,
    rationale: ci.rationale,
    severity: ci.severity,
    alternatives: ci.alternative_actions
  }) AS ContraindicatedMedications;

// ============================================================
// TRAVERSAL 5: Recommendation Version History
// Clinical Question: "How has the metformin recommendation changed?"
// Pattern: Recommendation -[:SUPERSEDES]-> older Recommendation
// ============================================================

MATCH path = (current:Recommendation {rec_id: 'REC_008'})
-[:SUPERSEDES*0..]->(historical:Recommendation)
RETURN
  [r IN nodes(path) | {
    rec_id: r.rec_id,
    version: r.version,
    date: r.version_date,
    text: r.rec_text,
    strength: r.strength,
    status: r.status
  }] AS VersionHistory;

// ============================================================
// TRAVERSAL 6: GRADE Decision Framework
// Clinical Question: "Why is the DSME recommendation Strong despite moderate evidence?"
// Pattern: Recommendation <- DecisionFramework -> Evidence + Benefits + Harms
// ============================================================

MATCH (r:Recommendation {rec_id: 'REC_007'})
<-[:DETERMINES]-(df:DecisionFramework)
-[:CONSIDERS]->(eb:EvidenceBody)
OPTIONAL MATCH (df)-[:WEIGHS]->(b:Benefit)
OPTIONAL MATCH (df)-[:WEIGHS]->(ae:AdverseEvent)
RETURN
  r.rec_text AS Recommendation,
  r.strength AS Strength,
  df.confidence_in_evidence AS EvidenceQuality,
  df.balance_of_outcomes AS BenefitHarmBalance,
  df.patient_values AS PatientValues,
  df.overall_judgment AS Rationale,
  collect(DISTINCT b.name) AS BenefitsConsidered,
  collect(DISTINCT ae.name) AS HarmsConsidered;

// ============================================================
// TRAVERSAL 7: Full Evidence Chain (Multi-Hop)
// Clinical Question: "Trace from a study all the way to clinical scenarios"
// Pattern: Study -> EvidenceBody -> Recommendation -> ClinicalScenario
// ============================================================

MATCH (s:Study {study_id: 'STUDY_UKPDS34'})
<-[:INCLUDES]-(eb:EvidenceBody)
-[:SUPPORTS]->(r:Recommendation)
<-[:TRIGGERS]-(cs:ClinicalScenario)
WHERE r.status = 'Active'
RETURN
  s.title AS Study,
  s.year AS Year,
  eb.topic AS EvidenceTopic,
  eb.quality_rating AS Quality,
  r.rec_text AS Recommendation,
  r.strength AS Strength,
  collect(DISTINCT cs.name) AS ApplicableScenarios;
