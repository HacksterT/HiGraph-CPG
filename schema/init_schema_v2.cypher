// =============================================================================
// HiGraph-CPG Schema V2 - Master Initialization Script
// =============================================================================
// This script initializes the complete V2 schema including:
// - Unique constraints (8)
// - Property indexes (12)
// - Full-text indexes (4)
// - Vector indexes (4)
//
// Run order matters: constraints must be created before property indexes.
//
// Usage:
//   Neo4j Browser: Copy and paste sections
//   cypher-shell: cat schema/init_schema_v2.cypher | cypher-shell -u neo4j -p <password>
//   Python: Use scripts/init_schema_v2.py
// =============================================================================

// =============================================================================
// SECTION 1: UNIQUE CONSTRAINTS
// =============================================================================

// Guideline - Document container
CREATE CONSTRAINT guideline_id_unique IF NOT EXISTS
FOR (g:Guideline) REQUIRE g.guideline_id IS UNIQUE;

// CarePhase - Clinical workflow stage
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

// Intervention - Treatment/action
CREATE CONSTRAINT intervention_id_unique IF NOT EXISTS
FOR (i:Intervention) REQUIRE i.intervention_id IS UNIQUE;

// Condition - Disease entity with ICD-10
CREATE CONSTRAINT condition_id_unique IF NOT EXISTS
FOR (c:Condition) REQUIRE c.condition_id IS UNIQUE;

// =============================================================================
// SECTION 2: PROPERTY INDEXES
// =============================================================================

// Study indexes
CREATE INDEX study_pmid IF NOT EXISTS FOR (s:Study) ON (s.pmid);
CREATE INDEX study_year IF NOT EXISTS FOR (s:Study) ON (s.year);
CREATE INDEX study_type IF NOT EXISTS FOR (s:Study) ON (s.study_type);

// Recommendation indexes
CREATE INDEX rec_strength_direction IF NOT EXISTS FOR (r:Recommendation) ON (r.strength_direction);
CREATE INDEX rec_category IF NOT EXISTS FOR (r:Recommendation) ON (r.category);
CREATE INDEX rec_topic IF NOT EXISTS FOR (r:Recommendation) ON (r.topic);

// EvidenceBody indexes
CREATE INDEX eb_quality IF NOT EXISTS FOR (eb:EvidenceBody) ON (eb.quality_rating);

// Intervention indexes
CREATE INDEX intervention_type IF NOT EXISTS FOR (i:Intervention) ON (i.type);
CREATE INDEX intervention_name IF NOT EXISTS FOR (i:Intervention) ON (i.name);
CREATE INDEX intervention_drug_class IF NOT EXISTS FOR (i:Intervention) ON (i.drug_class);

// Condition indexes
CREATE INDEX condition_name IF NOT EXISTS FOR (c:Condition) ON (c.name);
CREATE INDEX condition_icd10 IF NOT EXISTS FOR (c:Condition) ON (c.icd10_codes);

// CarePhase indexes
CREATE INDEX carephase_sequence IF NOT EXISTS FOR (cp:CarePhase) ON (cp.sequence_order);

// =============================================================================
// SECTION 3: FULL-TEXT INDEXES
// =============================================================================

CREATE FULLTEXT INDEX recommendation_fulltext IF NOT EXISTS
FOR (r:Recommendation) ON EACH [r.rec_text];

CREATE FULLTEXT INDEX carephase_fulltext IF NOT EXISTS
FOR (cp:CarePhase) ON EACH [cp.name, cp.description];

CREATE FULLTEXT INDEX condition_fulltext IF NOT EXISTS
FOR (c:Condition) ON EACH [c.name, c.definition, c.diagnostic_criteria];

CREATE FULLTEXT INDEX intervention_fulltext IF NOT EXISTS
FOR (i:Intervention) ON EACH [i.name, i.description, i.mechanism];

// =============================================================================
// SECTION 4: VECTOR INDEXES
// =============================================================================

CREATE VECTOR INDEX recommendation_embedding IF NOT EXISTS
FOR (r:Recommendation) ON (r.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}};

CREATE VECTOR INDEX study_embedding IF NOT EXISTS
FOR (s:Study) ON (s.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}};

CREATE VECTOR INDEX keyquestion_embedding IF NOT EXISTS
FOR (kq:KeyQuestion) ON (kq.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}};

CREATE VECTOR INDEX evidencebody_embedding IF NOT EXISTS
FOR (eb:EvidenceBody) ON (eb.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}};

// =============================================================================
// VERIFICATION
// =============================================================================
// Run these queries to verify schema was created correctly:
//
// SHOW CONSTRAINTS;
// SHOW INDEXES;
// SHOW INDEXES WHERE type = "FULLTEXT";
// SHOW INDEXES WHERE type = "VECTOR" YIELD name, state RETURN name, state;
// =============================================================================
