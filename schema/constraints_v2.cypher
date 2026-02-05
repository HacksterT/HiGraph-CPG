// =============================================================================
// HiGraph-CPG Schema V2 - Unique Constraints
// =============================================================================
// These constraints ensure data integrity and automatically create indexes
// on the constrained properties.
//
// Run with: cat schema/constraints_v2.cypher | cypher-shell -u neo4j -p <password>
// Or execute in Neo4j Browser
// =============================================================================

// -----------------------------------------------------------------------------
// Drop existing constraints (if migrating from V1)
// -----------------------------------------------------------------------------
// Uncomment these lines if you need to drop V1 constraints first:
// DROP CONSTRAINT guideline_id_unique IF EXISTS;
// DROP CONSTRAINT clinicalmodule_id_unique IF EXISTS;
// DROP CONSTRAINT recommendation_id_unique IF EXISTS;
// DROP CONSTRAINT keyquestion_id_unique IF EXISTS;
// DROP CONSTRAINT evidencebody_id_unique IF EXISTS;
// DROP CONSTRAINT study_id_unique IF EXISTS;

// -----------------------------------------------------------------------------
// V2 Unique Constraints (8 node types)
// -----------------------------------------------------------------------------

// Guideline - Document container
CREATE CONSTRAINT guideline_id_unique IF NOT EXISTS
FOR (g:Guideline) REQUIRE g.guideline_id IS UNIQUE;

// CarePhase - Clinical workflow stage (replaces ClinicalModule)
CREATE CONSTRAINT carephase_id_unique IF NOT EXISTS
FOR (cp:CarePhase) REQUIRE cp.phase_id IS UNIQUE;

// Recommendation - Clinical action statement
CREATE CONSTRAINT recommendation_id_unique IF NOT EXISTS
FOR (r:Recommendation) REQUIRE r.rec_id IS UNIQUE;

// KeyQuestion - PICOT research question
CREATE CONSTRAINT keyquestion_id_unique IF NOT EXISTS
FOR (kq:KeyQuestion) REQUIRE kq.kq_id IS UNIQUE;

// EvidenceBody - Synthesized evidence
CREATE CONSTRAINT evidencebody_id_unique IF NOT EXISTS
FOR (eb:EvidenceBody) REQUIRE eb.eb_id IS UNIQUE;

// Study - Research paper
CREATE CONSTRAINT study_id_unique IF NOT EXISTS
FOR (s:Study) REQUIRE s.study_id IS UNIQUE;

// Intervention - Treatment/action (NEW in V2)
CREATE CONSTRAINT intervention_id_unique IF NOT EXISTS
FOR (i:Intervention) REQUIRE i.intervention_id IS UNIQUE;

// Condition - Disease entity with ICD-10 (NEW in V2)
CREATE CONSTRAINT condition_id_unique IF NOT EXISTS
FOR (c:Condition) REQUIRE c.condition_id IS UNIQUE;

// -----------------------------------------------------------------------------
// Verification query
// -----------------------------------------------------------------------------
// Run this to verify constraints were created:
// SHOW CONSTRAINTS;
