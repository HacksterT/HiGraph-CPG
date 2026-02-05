// HiGraph-CPG Schema Constraints
// Uniqueness constraints on primary identifiers for all 17 node types

// 1. Guideline
CREATE CONSTRAINT guideline_id_unique IF NOT EXISTS
FOR (g:Guideline) REQUIRE g.guideline_id IS UNIQUE;

// NOTE: Property existence (IS NOT NULL) constraints require Enterprise Edition.
// Required properties are enforced at the application layer (Python scripts) instead.

// 2. ClinicalModule
CREATE CONSTRAINT module_id_unique IF NOT EXISTS
FOR (m:ClinicalModule) REQUIRE m.module_id IS UNIQUE;

// 3. KeyQuestion
CREATE CONSTRAINT kq_id_unique IF NOT EXISTS
FOR (kq:KeyQuestion) REQUIRE kq.kq_id IS UNIQUE;

// 4. EvidenceBody
CREATE CONSTRAINT evidence_id_unique IF NOT EXISTS
FOR (eb:EvidenceBody) REQUIRE eb.evidence_id IS UNIQUE;

// 5. Study
CREATE CONSTRAINT study_id_unique IF NOT EXISTS
FOR (s:Study) REQUIRE s.study_id IS UNIQUE;

// 6. Recommendation
CREATE CONSTRAINT rec_id_unique IF NOT EXISTS
FOR (r:Recommendation) REQUIRE r.rec_id IS UNIQUE;

// 7. ClinicalScenario
CREATE CONSTRAINT scenario_id_unique IF NOT EXISTS
FOR (cs:ClinicalScenario) REQUIRE cs.scenario_id IS UNIQUE;

// 8. Intervention
CREATE CONSTRAINT intervention_id_unique IF NOT EXISTS
FOR (i:Intervention) REQUIRE i.intervention_id IS UNIQUE;

// 9. Outcome
CREATE CONSTRAINT outcome_id_unique IF NOT EXISTS
FOR (o:Outcome) REQUIRE o.outcome_id IS UNIQUE;

// 10. OutcomeMeasurement
CREATE CONSTRAINT measurement_id_unique IF NOT EXISTS
FOR (om:OutcomeMeasurement) REQUIRE om.measurement_id IS UNIQUE;

// 11. Benefit
CREATE CONSTRAINT benefit_id_unique IF NOT EXISTS
FOR (b:Benefit) REQUIRE b.benefit_id IS UNIQUE;

// 12. AdverseEvent
CREATE CONSTRAINT ae_id_unique IF NOT EXISTS
FOR (ae:AdverseEvent) REQUIRE ae.ae_id IS UNIQUE;

// 13. PatientPopulation
CREATE CONSTRAINT population_id_unique IF NOT EXISTS
FOR (pp:PatientPopulation) REQUIRE pp.population_id IS UNIQUE;

// 14. PatientCharacteristic
CREATE CONSTRAINT characteristic_id_unique IF NOT EXISTS
FOR (pc:PatientCharacteristic) REQUIRE pc.characteristic_id IS UNIQUE;

// 15. Contraindication
CREATE CONSTRAINT contraindication_id_unique IF NOT EXISTS
FOR (ci:Contraindication) REQUIRE ci.contraindication_id IS UNIQUE;

// 16. QualityAssessment
CREATE CONSTRAINT assessment_id_unique IF NOT EXISTS
FOR (qa:QualityAssessment) REQUIRE qa.assessment_id IS UNIQUE;

// 17. DecisionFramework
CREATE CONSTRAINT framework_id_unique IF NOT EXISTS
FOR (df:DecisionFramework) REQUIRE df.framework_id IS UNIQUE;
