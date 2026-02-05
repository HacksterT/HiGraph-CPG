// HiGraph-CPG Seed Test Data
// Realistic diabetes CPG sample data covering all 17 entity types and key relationship patterns
//
// Usage: Execute via scripts/run_traversals.py or paste into Neo4j Browser

// ============================================================
// 1. GUIDELINE
// ============================================================
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
});

// ============================================================
// 2. CLINICAL MODULES
// ============================================================
CREATE (m1:ClinicalModule {
  module_id: "MOD_PHARM_001",
  module_name: "Pharmacotherapy",
  description: "Medication management for glycemic control",
  guideline_id: "CPG_DM_2023",
  sequence_order: 3
});

CREATE (m2:ClinicalModule {
  module_id: "MOD_DSME_001",
  module_name: "Diabetes Self-Management Education",
  description: "Patient education and self-management support",
  guideline_id: "CPG_DM_2023",
  sequence_order: 2
});

CREATE (m3:ClinicalModule {
  module_id: "MOD_LIFESTYLE_001",
  module_name: "Lifestyle Modification",
  description: "Diet, exercise, and behavioral interventions",
  guideline_id: "CPG_DM_2023",
  sequence_order: 1
});

// Module -> Guideline relationships
MATCH (m:ClinicalModule), (g:Guideline {guideline_id: "CPG_DM_2023"})
WHERE m.guideline_id = "CPG_DM_2023"
CREATE (m)-[:PART_OF]->(g);

// ============================================================
// 3. KEY QUESTIONS
// ============================================================
CREATE (kq1:KeyQuestion {
  kq_id: "KQ_005",
  kq_number: 5,
  question_text: "In adults with T2DM, what is the comparative effectiveness of pharmacologic interventions?",
  population: "Nonpregnant adults age >=18 with T2DM",
  intervention: "Pharmacologic agents (metformin, GLP-1 RA, SGLT-2i, DPP-4i, insulin)",
  comparator: "Placebo or active comparator",
  outcomes_critical: ["HbA1c", "CV mortality", "All-cause mortality", "Hypoglycemia"],
  outcomes_important: ["Weight change", "Quality of life"],
  timing: "Short-term and long-term outcomes",
  setting: "Primary care, outpatient",
  module_id: "MOD_PHARM_001",
  guideline_id: "CPG_DM_2023"
});

CREATE (kq2:KeyQuestion {
  kq_id: "KQ_003",
  kq_number: 3,
  question_text: "In adults with T2DM, what is the effectiveness of diabetes self-management education and support?",
  population: "Nonpregnant adults age >=18 with T2DM",
  intervention: "DSME/DSMS programs",
  comparator: "Standard care without structured DSME",
  outcomes_critical: ["HbA1c", "Self-care behaviors"],
  outcomes_important: ["Quality of life", "Patient satisfaction"],
  timing: "3-12 months",
  setting: "Primary care, outpatient, community",
  module_id: "MOD_DSME_001",
  guideline_id: "CPG_DM_2023"
});

// KQ -> Module relationships
MATCH (kq:KeyQuestion {kq_id: "KQ_005"}), (m:ClinicalModule {module_id: "MOD_PHARM_001"})
CREATE (kq)-[:ADDRESSES]->(m);
MATCH (kq:KeyQuestion {kq_id: "KQ_003"}), (m:ClinicalModule {module_id: "MOD_DSME_001"})
CREATE (kq)-[:ADDRESSES]->(m);

// Module -> KQ relationships
MATCH (m:ClinicalModule {module_id: "MOD_PHARM_001"}), (kq:KeyQuestion {kq_id: "KQ_005"})
CREATE (m)-[:CONTAINS]->(kq);
MATCH (m:ClinicalModule {module_id: "MOD_DSME_001"}), (kq:KeyQuestion {kq_id: "KQ_003"})
CREATE (m)-[:CONTAINS]->(kq);

// ============================================================
// 4. STUDIES
// ============================================================
CREATE (s1:Study {
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
});

CREATE (s2:Study {
  study_id: "STUDY_LEADER",
  pmid: "27295427",
  doi: "10.1056/NEJMoa1603827",
  title: "Liraglutide and Cardiovascular Outcomes in Type 2 Diabetes",
  authors: "Marso SP et al",
  journal: "N Engl J Med",
  year: 2016,
  study_type: "RCT",
  study_quality: "Good",
  sample_size: 9340,
  duration_weeks: 188,
  setting: "Multi-center",
  country: "Multi-national"
});

CREATE (s3:Study {
  study_id: "STUDY_DSME_META",
  pmid: "26710853",
  title: "Diabetes Self-Management Education and Support: A Systematic Review",
  authors: "Powers MA et al",
  journal: "Diabetes Care",
  year: 2015,
  study_type: "Systematic Review",
  study_quality: "Good",
  sample_size: 12500,
  setting: "Mixed settings",
  country: "Multi-national"
});

CREATE (s4:Study {
  study_id: "STUDY_EMPAREG",
  pmid: "26378978",
  doi: "10.1056/NEJMoa1515920",
  title: "Empagliflozin, Cardiovascular Outcomes, and Mortality in Type 2 Diabetes",
  authors: "Zinman B et al",
  journal: "N Engl J Med",
  year: 2015,
  study_type: "RCT",
  study_quality: "Good",
  sample_size: 7020,
  duration_weeks: 164,
  setting: "Multi-center",
  country: "Multi-national"
});

// ============================================================
// 5. EVIDENCE BODIES
// ============================================================
CREATE (eb1:EvidenceBody {
  evidence_id: "EVB_METFORMIN_001",
  topic: "Metformin efficacy and safety in T2DM",
  quality_rating: "High",
  confidence_level: "High confidence in estimate of effect",
  num_studies: 12,
  study_types: ["RCT", "Systematic Review"],
  date_synthesized: date("2022-04-11"),
  population_description: "Adults with T2DM in primary care settings",
  key_findings: "Metformin reduces HbA1c by 1.5% vs placebo with low risk of hypoglycemia and neutral/beneficial weight effects",
  guideline_id: "CPG_DM_2023",
  kq_id: "KQ_005",
  version: "6.0"
});

CREATE (eb2:EvidenceBody {
  evidence_id: "EVB_GLP1RA_CV_001",
  topic: "GLP-1 RA cardiovascular outcomes",
  quality_rating: "High",
  confidence_level: "High confidence in cardiovascular benefit",
  num_studies: 8,
  study_types: ["RCT"],
  date_synthesized: date("2022-06-15"),
  population_description: "Adults with T2DM and established ASCVD",
  key_findings: "GLP-1 RAs reduce major adverse cardiovascular events (MACE) by 12-14% vs placebo",
  guideline_id: "CPG_DM_2023",
  kq_id: "KQ_005",
  version: "6.0"
});

CREATE (eb3:EvidenceBody {
  evidence_id: "EVB_DSME_001",
  topic: "Effectiveness of DSME/DSMS programs",
  quality_rating: "Moderate",
  confidence_level: "Moderate confidence in estimate of effect",
  num_studies: 15,
  study_types: ["RCT", "Systematic Review"],
  date_synthesized: date("2022-03-20"),
  population_description: "Adults with T2DM across clinical settings",
  key_findings: "DSME improves HbA1c by 0.5-1.0%, improves self-care behaviors, and increases quality of life",
  guideline_id: "CPG_DM_2023",
  kq_id: "KQ_003",
  version: "6.0"
});

// Evidence -> Study relationships
MATCH (eb:EvidenceBody {evidence_id: "EVB_METFORMIN_001"}), (s:Study {study_id: "STUDY_UKPDS34"})
CREATE (eb)-[:INCLUDES]->(s);
MATCH (eb:EvidenceBody {evidence_id: "EVB_GLP1RA_CV_001"}), (s:Study {study_id: "STUDY_LEADER"})
CREATE (eb)-[:INCLUDES]->(s);
MATCH (eb:EvidenceBody {evidence_id: "EVB_GLP1RA_CV_001"}), (s:Study {study_id: "STUDY_EMPAREG"})
CREATE (eb)-[:INCLUDES]->(s);
MATCH (eb:EvidenceBody {evidence_id: "EVB_DSME_001"}), (s:Study {study_id: "STUDY_DSME_META"})
CREATE (eb)-[:INCLUDES]->(s);

// Evidence -> KQ relationships
MATCH (eb:EvidenceBody {evidence_id: "EVB_METFORMIN_001"}), (kq:KeyQuestion {kq_id: "KQ_005"})
CREATE (eb)-[:ANSWERS]->(kq);
MATCH (eb:EvidenceBody {evidence_id: "EVB_GLP1RA_CV_001"}), (kq:KeyQuestion {kq_id: "KQ_005"})
CREATE (eb)-[:ANSWERS]->(kq);
MATCH (eb:EvidenceBody {evidence_id: "EVB_DSME_001"}), (kq:KeyQuestion {kq_id: "KQ_003"})
CREATE (eb)-[:ANSWERS]->(kq);

// ============================================================
// 6. RECOMMENDATIONS
// ============================================================
CREATE (r1:Recommendation {
  rec_id: "REC_008",
  rec_number: 8,
  rec_text: "In adults with newly diagnosed T2DM, we recommend metformin as first-line pharmacotherapy in addition to lifestyle modifications.",
  strength: "Strong",
  direction: "For",
  category: "Not changed",
  topic: "Pharmacotherapy",
  subtopic: "First-line therapy",
  module_id: "MOD_PHARM_001",
  guideline_id: "CPG_DM_2023",
  version: "6.0",
  version_date: date("2023-05-01"),
  status: "Active",
  implementation_considerations: "Metformin widely available as generic; start low dose and titrate"
});

CREATE (r2:Recommendation {
  rec_id: "REC_015",
  rec_number: 15,
  rec_text: "In adults with T2DM and established ASCVD, we suggest adding a GLP-1 receptor agonist with proven cardiovascular benefit.",
  strength: "Weak",
  direction: "For",
  category: "New-added",
  topic: "Pharmacotherapy",
  subtopic: "Cardiovascular risk reduction",
  module_id: "MOD_PHARM_001",
  guideline_id: "CPG_DM_2023",
  version: "6.0",
  version_date: date("2023-05-01"),
  status: "Active",
  implementation_considerations: "Consider patient preference, cost, and injection burden"
});

CREATE (r3:Recommendation {
  rec_id: "REC_007",
  rec_number: 7,
  rec_text: "In adults with type 2 diabetes mellitus, we recommend diabetes self-management education and support.",
  strength: "Strong",
  direction: "For",
  category: "Not changed",
  topic: "Diabetes Self-Management Education and Support",
  module_id: "MOD_DSME_001",
  guideline_id: "CPG_DM_2023",
  version: "6.0",
  version_date: date("2023-05-01"),
  status: "Active",
  implementation_considerations: "DSME programs widely available in VA/DoD facilities"
});

// Superseded (old) version of REC_008 for versioning demo
CREATE (r_old:Recommendation {
  rec_id: "REC_008_v5",
  rec_number: 8,
  rec_text: "We recommend lifestyle modification plus metformin for patients with newly diagnosed T2DM.",
  strength: "Strong",
  direction: "For",
  category: "Not changed",
  topic: "Pharmacotherapy",
  subtopic: "First-line therapy",
  module_id: "MOD_PHARM_001",
  guideline_id: "CPG_DM_2023",
  version: "5.0",
  version_date: date("2020-04-01"),
  previous_version_id: null,
  status: "Superseded"
});

// Evidence -> Recommendation relationships
MATCH (eb:EvidenceBody {evidence_id: "EVB_METFORMIN_001"}), (r:Recommendation {rec_id: "REC_008"})
CREATE (eb)-[:SUPPORTS {strength: "Strong"}]->(r);
MATCH (eb:EvidenceBody {evidence_id: "EVB_GLP1RA_CV_001"}), (r:Recommendation {rec_id: "REC_015"})
CREATE (eb)-[:SUPPORTS {strength: "Moderate"}]->(r);
MATCH (eb:EvidenceBody {evidence_id: "EVB_DSME_001"}), (r:Recommendation {rec_id: "REC_007"})
CREATE (eb)-[:SUPPORTS {strength: "Moderate"}]->(r);

// Recommendation -> EvidenceBody (BASED_ON)
MATCH (r:Recommendation {rec_id: "REC_008"}), (eb:EvidenceBody {evidence_id: "EVB_METFORMIN_001"})
CREATE (r)-[:BASED_ON]->(eb);
MATCH (r:Recommendation {rec_id: "REC_015"}), (eb:EvidenceBody {evidence_id: "EVB_GLP1RA_CV_001"})
CREATE (r)-[:BASED_ON]->(eb);
MATCH (r:Recommendation {rec_id: "REC_007"}), (eb:EvidenceBody {evidence_id: "EVB_DSME_001"})
CREATE (r)-[:BASED_ON]->(eb);

// Versioning: REC_008 supersedes REC_008_v5
MATCH (r_new:Recommendation {rec_id: "REC_008"}), (r_old:Recommendation {rec_id: "REC_008_v5"})
CREATE (r_new)-[:SUPERSEDES {reason: "Updated evidence synthesis", date: date("2023-05-01")}]->(r_old);

// ============================================================
// 7. CLINICAL SCENARIOS
// ============================================================
CREATE (cs1:ClinicalScenario {
  scenario_id: "CS_NEWDX_T2DM",
  name: "Newly diagnosed T2DM, no complications",
  description: "Adult patient with recent T2DM diagnosis, no known microvascular or macrovascular complications, eGFR >60",
  prevalence: "Common",
  urgency: "Routine",
  decision_points: ["First-line therapy selection", "Glycemic target setting", "Monitoring frequency"],
  guideline_id: "CPG_DM_2023"
});

CREATE (cs2:ClinicalScenario {
  scenario_id: "CS_T2DM_ASCVD",
  name: "T2DM with established ASCVD",
  description: "Adult patient with T2DM and history of myocardial infarction, stroke, or peripheral arterial disease",
  prevalence: "Common",
  urgency: "Urgent",
  decision_points: ["CV risk reduction agent selection", "Dual therapy considerations"],
  guideline_id: "CPG_DM_2023"
});

// Scenario -> Recommendation (TRIGGERS)
MATCH (cs:ClinicalScenario {scenario_id: "CS_NEWDX_T2DM"}), (r:Recommendation {rec_id: "REC_008"})
CREATE (cs)-[:TRIGGERS {priority: 1}]->(r);
MATCH (cs:ClinicalScenario {scenario_id: "CS_NEWDX_T2DM"}), (r:Recommendation {rec_id: "REC_007"})
CREATE (cs)-[:TRIGGERS {priority: 1}]->(r);
MATCH (cs:ClinicalScenario {scenario_id: "CS_T2DM_ASCVD"}), (r:Recommendation {rec_id: "REC_015"})
CREATE (cs)-[:TRIGGERS {priority: 1}]->(r);
MATCH (cs:ClinicalScenario {scenario_id: "CS_T2DM_ASCVD"}), (r:Recommendation {rec_id: "REC_008"})
CREATE (cs)-[:TRIGGERS {priority: 2}]->(r);

// ============================================================
// 8. INTERVENTIONS
// ============================================================
CREATE (i1:Intervention {
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
});

CREATE (i2:Intervention {
  intervention_id: "INT_GLP1RA",
  name: "GLP-1 Receptor Agonist",
  generic_name: "Liraglutide / Semaglutide",
  drug_class: "GLP-1 RA",
  type: "Pharmacologic",
  mechanism: "Incretin mimetic; enhances glucose-dependent insulin secretion, suppresses glucagon",
  typical_dose: "Varies by agent",
  administration: "Subcutaneous injection or oral (semaglutide)",
  cost_category: "High",
  availability: "Brand only for most agents"
});

CREATE (i3:Intervention {
  intervention_id: "INT_SGLT2I",
  name: "SGLT-2 Inhibitor",
  generic_name: "Empagliflozin / Dapagliflozin",
  drug_class: "SGLT-2 Inhibitor",
  type: "Pharmacologic",
  mechanism: "Inhibits renal glucose reabsorption in proximal tubule",
  typical_dose: "10-25 mg daily (empagliflozin)",
  administration: "Oral",
  cost_category: "High",
  availability: "Brand; some generics emerging"
});

CREATE (i4:Intervention {
  intervention_id: "INT_DSME",
  name: "Diabetes Self-Management Education",
  type: "Non-pharmacologic",
  mechanism: "Structured education on self-monitoring, nutrition, physical activity, medication adherence",
  availability: "Widely available in VA/DoD"
});

CREATE (i5:Intervention {
  intervention_id: "INT_LIFESTYLE",
  name: "Lifestyle Modification",
  type: "Non-pharmacologic",
  mechanism: "Diet, exercise, weight management, and behavioral change",
  availability: "Universally available"
});

// Recommendation -> Intervention (RECOMMENDS)
MATCH (r:Recommendation {rec_id: "REC_008"}), (i:Intervention {intervention_id: "INT_METFORMIN"})
CREATE (r)-[:RECOMMENDS {preference: "preferred"}]->(i);
MATCH (r:Recommendation {rec_id: "REC_008"}), (i:Intervention {intervention_id: "INT_LIFESTYLE"})
CREATE (r)-[:RECOMMENDS {preference: "preferred"}]->(i);
MATCH (r:Recommendation {rec_id: "REC_015"}), (i:Intervention {intervention_id: "INT_GLP1RA"})
CREATE (r)-[:RECOMMENDS {preference: "preferred"}]->(i);
MATCH (r:Recommendation {rec_id: "REC_007"}), (i:Intervention {intervention_id: "INT_DSME"})
CREATE (r)-[:RECOMMENDS {preference: "preferred"}]->(i);

// Intervention -> Intervention (ALTERNATIVE_TO)
MATCH (a:Intervention {intervention_id: "INT_GLP1RA"}), (b:Intervention {intervention_id: "INT_SGLT2I"})
CREATE (a)-[:ALTERNATIVE_TO {context: "Both have CV benefit; choice based on patient factors"}]->(b);

// ============================================================
// 9. OUTCOMES
// ============================================================
CREATE (o1:Outcome {
  outcome_id: "OUT_HBA1C",
  name: "HbA1c",
  description: "Glycated hemoglobin A1c",
  measurement_method: "Laboratory assay, percentage or mmol/mol",
  criticality: "Critical",
  outcome_category: "Glycemic"
});

CREATE (o2:Outcome {
  outcome_id: "OUT_CV_MORTALITY",
  name: "Cardiovascular mortality",
  description: "Death from cardiovascular causes",
  measurement_method: "Adjudicated clinical events",
  criticality: "Critical",
  outcome_category: "Cardiovascular"
});

// ============================================================
// 10. OUTCOME MEASUREMENTS
// ============================================================
CREATE (om1:OutcomeMeasurement {
  measurement_id: "MEAS_UKPDS_HBA1C",
  study_id: "STUDY_UKPDS34",
  outcome_id: "OUT_HBA1C",
  intervention_id: "INT_METFORMIN",
  value: "-1.5%",
  value_numeric: -1.5,
  unit: "percentage points",
  timeframe: "10 years median follow-up",
  statistical_significance: "p<0.001",
  effect_size: "Large clinically significant reduction"
});

CREATE (om2:OutcomeMeasurement {
  measurement_id: "MEAS_LEADER_CV",
  study_id: "STUDY_LEADER",
  outcome_id: "OUT_CV_MORTALITY",
  intervention_id: "INT_GLP1RA",
  value: "HR 0.78",
  value_numeric: 0.78,
  unit: "hazard ratio",
  timeframe: "3.8 years median",
  statistical_significance: "p=0.007",
  effect_size: "22% relative risk reduction in CV death"
});

// OutcomeMeasurement relationships
MATCH (om:OutcomeMeasurement {measurement_id: "MEAS_UKPDS_HBA1C"}), (o:Outcome {outcome_id: "OUT_HBA1C"})
CREATE (om)-[:MEASURES_OUTCOME]->(o);
MATCH (om:OutcomeMeasurement {measurement_id: "MEAS_UKPDS_HBA1C"}), (s:Study {study_id: "STUDY_UKPDS34"})
CREATE (om)-[:FROM_STUDY]->(s);
MATCH (om:OutcomeMeasurement {measurement_id: "MEAS_LEADER_CV"}), (o:Outcome {outcome_id: "OUT_CV_MORTALITY"})
CREATE (om)-[:MEASURES_OUTCOME]->(o);
MATCH (om:OutcomeMeasurement {measurement_id: "MEAS_LEADER_CV"}), (s:Study {study_id: "STUDY_LEADER"})
CREATE (om)-[:FROM_STUDY]->(s);

// Study -> OutcomeMeasurement (MEASURES)
MATCH (s:Study {study_id: "STUDY_UKPDS34"}), (om:OutcomeMeasurement {measurement_id: "MEAS_UKPDS_HBA1C"})
CREATE (s)-[:MEASURES]->(om);
MATCH (s:Study {study_id: "STUDY_LEADER"}), (om:OutcomeMeasurement {measurement_id: "MEAS_LEADER_CV"})
CREATE (s)-[:MEASURES]->(om);

// ============================================================
// 11. BENEFITS
// ============================================================
CREATE (b1:Benefit {
  benefit_id: "BEN_METFORMIN_HBA1C",
  name: "HbA1c reduction",
  description: "Decrease in glycated hemoglobin with metformin therapy",
  magnitude: "1.5%",
  magnitude_type: "Absolute",
  criticality: "Critical",
  timeframe: "3-6 months",
  confidence: "High",
  clinical_significance: "Clinically meaningful reduction associated with decreased microvascular complications"
});

CREATE (b2:Benefit {
  benefit_id: "BEN_GLP1RA_CV",
  name: "Cardiovascular mortality reduction",
  description: "Reduction in CV death with GLP-1 receptor agonists",
  magnitude: "22% relative reduction",
  magnitude_type: "Relative",
  criticality: "Critical",
  timeframe: "3-5 years",
  confidence: "High",
  clinical_significance: "Major survival benefit in patients with ASCVD"
});

CREATE (b3:Benefit {
  benefit_id: "BEN_METFORMIN_WEIGHT",
  name: "Weight neutral or loss",
  description: "Metformin does not cause weight gain and may produce modest weight loss",
  magnitude: "0-2 kg loss",
  magnitude_type: "Absolute",
  criticality: "Important",
  timeframe: "6-12 months",
  confidence: "Moderate",
  clinical_significance: "Favorable compared to sulfonylureas or insulin"
});

// Intervention -> Benefit (PRODUCES)
MATCH (i:Intervention {intervention_id: "INT_METFORMIN"}), (b:Benefit {benefit_id: "BEN_METFORMIN_HBA1C"})
CREATE (i)-[:PRODUCES {magnitude: "1.5% HbA1c reduction"}]->(b);
MATCH (i:Intervention {intervention_id: "INT_METFORMIN"}), (b:Benefit {benefit_id: "BEN_METFORMIN_WEIGHT"})
CREATE (i)-[:PRODUCES {magnitude: "0-2 kg loss"}]->(b);
MATCH (i:Intervention {intervention_id: "INT_GLP1RA"}), (b:Benefit {benefit_id: "BEN_GLP1RA_CV"})
CREATE (i)-[:PRODUCES {magnitude: "22% CV mortality reduction"}]->(b);

// Study -> Benefit (DEMONSTRATES)
MATCH (s:Study {study_id: "STUDY_UKPDS34"}), (b:Benefit {benefit_id: "BEN_METFORMIN_HBA1C"})
CREATE (s)-[:DEMONSTRATES]->(b);
MATCH (s:Study {study_id: "STUDY_LEADER"}), (b:Benefit {benefit_id: "BEN_GLP1RA_CV"})
CREATE (s)-[:DEMONSTRATES]->(b);

// ============================================================
// 12. ADVERSE EVENTS
// ============================================================
CREATE (ae1:AdverseEvent {
  ae_id: "AE_METFORMIN_GI",
  name: "Gastrointestinal side effects",
  description: "Nausea, diarrhea, abdominal discomfort associated with metformin",
  severity: "Moderate",
  frequency: "20-30%",
  frequency_type: "Percentage",
  onset: "Early (first few weeks)",
  duration: "Usually transient, resolves with continued use or dose reduction",
  management: "Start low dose, titrate slowly, take with food, consider extended-release formulation",
  criticality: "Important",
  reversibility: "Reversible"
});

CREATE (ae2:AdverseEvent {
  ae_id: "AE_METFORMIN_LACTIC",
  name: "Lactic acidosis",
  description: "Rare but serious metabolic complication from metformin accumulation",
  severity: "Life-threatening",
  frequency: "Rare (<0.01%)",
  frequency_type: "Percentage",
  onset: "Variable",
  management: "Discontinue metformin; supportive care including hemodialysis",
  criticality: "Critical",
  reversibility: "Variable"
});

CREATE (ae3:AdverseEvent {
  ae_id: "AE_GLP1RA_GI",
  name: "GLP-1 RA gastrointestinal effects",
  description: "Nausea, vomiting, diarrhea with GLP-1 receptor agonist therapy",
  severity: "Moderate",
  frequency: "15-25%",
  frequency_type: "Percentage",
  onset: "Early (dose escalation phase)",
  management: "Slow dose titration, take with food",
  criticality: "Important",
  reversibility: "Reversible"
});

// Intervention -> AdverseEvent (CAUSES)
MATCH (i:Intervention {intervention_id: "INT_METFORMIN"}), (ae:AdverseEvent {ae_id: "AE_METFORMIN_GI"})
CREATE (i)-[:CAUSES {frequency: "20-30%"}]->(ae);
MATCH (i:Intervention {intervention_id: "INT_METFORMIN"}), (ae:AdverseEvent {ae_id: "AE_METFORMIN_LACTIC"})
CREATE (i)-[:CAUSES {frequency: "Rare"}]->(ae);
MATCH (i:Intervention {intervention_id: "INT_GLP1RA"}), (ae:AdverseEvent {ae_id: "AE_GLP1RA_GI"})
CREATE (i)-[:CAUSES {frequency: "15-25%"}]->(ae);

// ============================================================
// 13. PATIENT POPULATION
// ============================================================
CREATE (pp1:PatientPopulation {
  population_id: "POP_ADULTS_T2DM",
  name: "Adults with Type 2 Diabetes Mellitus",
  description: "Nonpregnant adults age >=18 years with diagnosed T2DM",
  age_range: ">=18 years",
  inclusion_criteria: ["Diagnosed T2DM", "Age >=18", "Non-pregnant"],
  exclusion_criteria: ["Type 1 diabetes", "Gestational diabetes", "Pregnancy"],
  prevalence_description: "Approximately 10-12% of US adult population",
  guideline_id: "CPG_DM_2023"
});

// ============================================================
// 14. PATIENT CHARACTERISTICS
// ============================================================
CREATE (pc1:PatientCharacteristic {
  characteristic_id: "PC_ASCVD",
  name: "Established ASCVD",
  description: "History of atherosclerotic cardiovascular disease including MI, stroke, or peripheral arterial disease",
  type: "Comorbidity",
  prevalence_in_population: "32% of adults with T2DM",
  clinical_impact: "High",
  modifies_treatment: true,
  measurement_method: "Clinical history, documented prior CV event"
});

CREATE (pc2:PatientCharacteristic {
  characteristic_id: "PC_RENAL_SEVERE",
  name: "Severe renal impairment",
  description: "eGFR <30 mL/min/1.73m2 (CKD Stage 4-5)",
  type: "Comorbidity",
  prevalence_in_population: "8% of adults with T2DM",
  clinical_impact: "High",
  modifies_treatment: true,
  measurement_method: "Laboratory eGFR calculation"
});

// PatientCharacteristic -> Recommendation (MODIFIES)
MATCH (pc:PatientCharacteristic {characteristic_id: "PC_ASCVD"}), (r:Recommendation {rec_id: "REC_015"})
CREATE (pc)-[:MODIFIES {impact: "strengthens", direction: "for"}]->(r);

// PatientCharacteristic -> AdverseEvent (INCREASES_RISK_OF)
MATCH (pc:PatientCharacteristic {characteristic_id: "PC_RENAL_SEVERE"}), (ae:AdverseEvent {ae_id: "AE_METFORMIN_LACTIC"})
CREATE (pc)-[:INCREASES_RISK_OF {magnitude: "Significantly increased"}]->(ae);

// ClinicalScenario -> PatientCharacteristic (REQUIRES)
MATCH (cs:ClinicalScenario {scenario_id: "CS_T2DM_ASCVD"}), (pc:PatientCharacteristic {characteristic_id: "PC_ASCVD"})
CREATE (cs)-[:REQUIRES]->(pc);

// ============================================================
// 15. CONTRAINDICATIONS
// ============================================================
CREATE (ci1:Contraindication {
  contraindication_id: "CI_METFORMIN_RENAL",
  type: "Absolute",
  condition: "Severe renal impairment (eGFR <30 mL/min)",
  rationale: "Risk of lactic acidosis due to metformin accumulation",
  evidence_quality: "Moderate",
  alternative_actions: "Use alternative agent such as DPP-4 inhibitor or insulin",
  severity: "Critical"
});

CREATE (ci2:Contraindication {
  contraindication_id: "CI_SGLT2I_RENAL",
  type: "Relative",
  condition: "Severe renal impairment (eGFR <20 mL/min)",
  rationale: "Reduced glycemic efficacy with very low GFR; may retain renal/CV benefits",
  evidence_quality: "Moderate",
  alternative_actions: "Consider GLP-1 RA or insulin for glycemic control",
  severity: "Important"
});

// Contraindication -> Intervention (CONTRAINDICATES)
MATCH (ci:Contraindication {contraindication_id: "CI_METFORMIN_RENAL"}), (i:Intervention {intervention_id: "INT_METFORMIN"})
CREATE (ci)-[:CONTRAINDICATES]->(i);
MATCH (ci:Contraindication {contraindication_id: "CI_SGLT2I_RENAL"}), (i:Intervention {intervention_id: "INT_SGLT2I"})
CREATE (ci)-[:CONTRAINDICATES]->(i);

// Contraindication -> PatientCharacteristic (APPLIES_TO)
MATCH (ci:Contraindication {contraindication_id: "CI_METFORMIN_RENAL"}), (pc:PatientCharacteristic {characteristic_id: "PC_RENAL_SEVERE"})
CREATE (ci)-[:APPLIES_TO]->(pc);
MATCH (ci:Contraindication {contraindication_id: "CI_SGLT2I_RENAL"}), (pc:PatientCharacteristic {characteristic_id: "PC_RENAL_SEVERE"})
CREATE (ci)-[:APPLIES_TO]->(pc);

// ============================================================
// 16. QUALITY ASSESSMENTS
// ============================================================
CREATE (qa1:QualityAssessment {
  assessment_id: "QA_METFORMIN_ROB",
  evidence_body_id: "EVB_METFORMIN_001",
  domain: "Risk of Bias",
  rating: "No serious issues",
  direction: "No change",
  justification: "All included RCTs rated Good quality by USPSTF criteria",
  assessor: "Evidence Review Team",
  assessment_date: date("2022-04-11")
});

// QualityAssessment -> EvidenceBody (EVALUATES)
MATCH (qa:QualityAssessment {assessment_id: "QA_METFORMIN_ROB"}), (eb:EvidenceBody {evidence_id: "EVB_METFORMIN_001"})
CREATE (qa)-[:EVALUATES]->(eb);

// ============================================================
// 17. DECISION FRAMEWORKS
// ============================================================
CREATE (df1:DecisionFramework {
  framework_id: "DF_007",
  recommendation_id: "REC_007",
  confidence_in_evidence: "Moderate",
  balance_of_outcomes: "Benefits outweigh harms",
  patient_values: "Patients highly value education and empowerment; DSME addresses patient-expressed needs for understanding their disease and self-management",
  other_implications: "DSME programs widely available in VA/DoD facilities. Ensures all patients receive standardized education. High acceptability.",
  overall_judgment: "Strong For recommendation despite moderate evidence quality due to clear benefits, patient values alignment, and minimal harms"
});

CREATE (df2:DecisionFramework {
  framework_id: "DF_008",
  recommendation_id: "REC_008",
  confidence_in_evidence: "High",
  balance_of_outcomes: "Benefits clearly outweigh harms",
  patient_values: "Patients prefer oral medication with low hypoglycemia risk; metformin meets both criteria",
  other_implications: "Low cost, generic availability, extensive safety record. Weight neutral advantage over alternatives.",
  overall_judgment: "Strong For recommendation supported by high-quality evidence, favorable benefit-harm balance, and strong patient values alignment"
});

// DecisionFramework -> Recommendation (DETERMINES)
MATCH (df:DecisionFramework {framework_id: "DF_007"}), (r:Recommendation {rec_id: "REC_007"})
CREATE (df)-[:DETERMINES]->(r);
MATCH (df:DecisionFramework {framework_id: "DF_008"}), (r:Recommendation {rec_id: "REC_008"})
CREATE (df)-[:DETERMINES]->(r);

// DecisionFramework -> EvidenceBody (CONSIDERS)
MATCH (df:DecisionFramework {framework_id: "DF_007"}), (eb:EvidenceBody {evidence_id: "EVB_DSME_001"})
CREATE (df)-[:CONSIDERS]->(eb);
MATCH (df:DecisionFramework {framework_id: "DF_008"}), (eb:EvidenceBody {evidence_id: "EVB_METFORMIN_001"})
CREATE (df)-[:CONSIDERS]->(eb);

// DecisionFramework -> Benefit (WEIGHS)
MATCH (df:DecisionFramework {framework_id: "DF_008"}), (b:Benefit {benefit_id: "BEN_METFORMIN_HBA1C"})
CREATE (df)-[:WEIGHS {weight: "critical"}]->(b);
MATCH (df:DecisionFramework {framework_id: "DF_008"}), (b:Benefit {benefit_id: "BEN_METFORMIN_WEIGHT"})
CREATE (df)-[:WEIGHS {weight: "important"}]->(b);

// DecisionFramework -> AdverseEvent (WEIGHS)
MATCH (df:DecisionFramework {framework_id: "DF_008"}), (ae:AdverseEvent {ae_id: "AE_METFORMIN_GI"})
CREATE (df)-[:WEIGHS {weight: "important"}]->(ae);

// DecisionFramework -> QualityAssessment (INFORMED_BY)
MATCH (df:DecisionFramework {framework_id: "DF_008"}), (qa:QualityAssessment {assessment_id: "QA_METFORMIN_ROB"})
CREATE (df)-[:INFORMED_BY]->(qa);
