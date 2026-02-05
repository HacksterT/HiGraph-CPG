// HiGraph-CPG Schema Indexes
// Standard and compound indexes for frequently queried properties

// --- Standard Indexes ---

// Guideline
CREATE INDEX guideline_disease IF NOT EXISTS
FOR (g:Guideline) ON (g.disease_condition);

CREATE INDEX guideline_status IF NOT EXISTS
FOR (g:Guideline) ON (g.status);

// Study
CREATE INDEX study_pmid IF NOT EXISTS
FOR (s:Study) ON (s.pmid);

// Recommendation
CREATE INDEX rec_strength IF NOT EXISTS
FOR (r:Recommendation) ON (r.strength);

CREATE INDEX rec_status IF NOT EXISTS
FOR (r:Recommendation) ON (r.status);

// Intervention
CREATE INDEX intervention_name IF NOT EXISTS
FOR (i:Intervention) ON (i.name);

CREATE INDEX intervention_class IF NOT EXISTS
FOR (i:Intervention) ON (i.drug_class);

// --- Compound Indexes ---

// Guideline + version lookups
CREATE INDEX guideline_version IF NOT EXISTS
FOR (g:Guideline) ON (g.guideline_id, g.version);

// Recommendation filtering by strength + direction
CREATE INDEX rec_strength_direction IF NOT EXISTS
FOR (r:Recommendation) ON (r.strength, r.direction);

// Study searches by year + type
CREATE INDEX study_year_type IF NOT EXISTS
FOR (s:Study) ON (s.year, s.study_type);

// Intervention queries by class + type
CREATE INDEX intervention_class_type IF NOT EXISTS
FOR (i:Intervention) ON (i.drug_class, i.type);
