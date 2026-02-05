// =============================================================================
// HiGraph-CPG Schema V2 - Property Indexes
// =============================================================================
// These indexes support common query patterns for filtering and lookup.
// Unique constraint indexes are created automatically, so these are
// additional indexes for non-unique properties.
//
// Run with: cat schema/indexes_v2.cypher | cypher-shell -u neo4j -p <password>
// Or execute in Neo4j Browser
// =============================================================================

// -----------------------------------------------------------------------------
// Study Indexes - Common lookups and filters
// -----------------------------------------------------------------------------

// PubMed ID lookup - very common query pattern
CREATE INDEX study_pmid IF NOT EXISTS
FOR (s:Study) ON (s.pmid);

// Year filter - "studies from last 5 years"
CREATE INDEX study_year IF NOT EXISTS
FOR (s:Study) ON (s.year);

// Study type filter - "all RCTs", "all systematic reviews"
CREATE INDEX study_type IF NOT EXISTS
FOR (s:Study) ON (s.study_type);

// -----------------------------------------------------------------------------
// Recommendation Indexes - Clinical query filters
// -----------------------------------------------------------------------------

// Strength/direction filter - "all Strong For recommendations"
CREATE INDEX rec_strength_direction IF NOT EXISTS
FOR (r:Recommendation) ON (r.strength_direction);

// Category filter - "all new recommendations", "all amended"
CREATE INDEX rec_category IF NOT EXISTS
FOR (r:Recommendation) ON (r.category);

// Topic filter - for grouping by clinical area
CREATE INDEX rec_topic IF NOT EXISTS
FOR (r:Recommendation) ON (r.topic);

// -----------------------------------------------------------------------------
// EvidenceBody Indexes
// -----------------------------------------------------------------------------

// Quality rating filter - "high quality evidence only"
CREATE INDEX eb_quality IF NOT EXISTS
FOR (eb:EvidenceBody) ON (eb.quality_rating);

// -----------------------------------------------------------------------------
// Intervention Indexes
// -----------------------------------------------------------------------------

// Type filter - "all drug interventions", "all lifestyle interventions"
CREATE INDEX intervention_type IF NOT EXISTS
FOR (i:Intervention) ON (i.type);

// Name lookup - "find intervention by name"
CREATE INDEX intervention_name IF NOT EXISTS
FOR (i:Intervention) ON (i.name);

// Drug class lookup - for hierarchical queries
CREATE INDEX intervention_drug_class IF NOT EXISTS
FOR (i:Intervention) ON (i.drug_class);

// -----------------------------------------------------------------------------
// Condition Indexes
// -----------------------------------------------------------------------------

// Name lookup - "find condition by name"
CREATE INDEX condition_name IF NOT EXISTS
FOR (c:Condition) ON (c.name);

// ICD-10 code lookup - "find by diagnosis code"
// Note: This indexes the array - queries use WHERE "E11" IN c.icd10_codes
CREATE INDEX condition_icd10 IF NOT EXISTS
FOR (c:Condition) ON (c.icd10_codes);

// -----------------------------------------------------------------------------
// CarePhase Indexes
// -----------------------------------------------------------------------------

// Sequence order - for ordered retrieval
CREATE INDEX carephase_sequence IF NOT EXISTS
FOR (cp:CarePhase) ON (cp.sequence_order);

// -----------------------------------------------------------------------------
// Verification query
// -----------------------------------------------------------------------------
// Run this to verify indexes were created:
// SHOW INDEXES;
