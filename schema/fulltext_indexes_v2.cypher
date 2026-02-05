// =============================================================================
// HiGraph-CPG Schema V2 - Full-Text Indexes
// =============================================================================
// Full-text indexes enable keyword search on text fields.
// Used for structured/shorter text where semantic search is less effective.
//
// Run with: cat schema/fulltext_indexes_v2.cypher | cypher-shell -u neo4j -p <password>
// Or execute in Neo4j Browser
// =============================================================================

// -----------------------------------------------------------------------------
// Drop existing full-text indexes (if migrating)
// -----------------------------------------------------------------------------
// Uncomment if needed:
// DROP INDEX recommendation_fulltext IF EXISTS;

// -----------------------------------------------------------------------------
// Recommendation Full-Text Index
// -----------------------------------------------------------------------------
// Primary clinical query surface - clinicians search for specific terms
// Example: "Find recommendations mentioning SGLT2"

CREATE FULLTEXT INDEX recommendation_fulltext IF NOT EXISTS
FOR (r:Recommendation)
ON EACH [r.rec_text];

// Usage:
// CALL db.index.fulltext.queryNodes("recommendation_fulltext", "SGLT2")
// YIELD node, score
// RETURN node.rec_id, node.rec_text, score
// ORDER BY score DESC
// LIMIT 10;

// -----------------------------------------------------------------------------
// CarePhase Full-Text Index
// -----------------------------------------------------------------------------
// Clinical pathway queries - search by phase name or description
// Example: "Find care phases related to screening"

CREATE FULLTEXT INDEX carephase_fulltext IF NOT EXISTS
FOR (cp:CarePhase)
ON EACH [cp.name, cp.description];

// Usage:
// CALL db.index.fulltext.queryNodes("carephase_fulltext", "screening prevention")
// YIELD node, score
// RETURN node.phase_id, node.name, score
// ORDER BY score DESC;

// -----------------------------------------------------------------------------
// Condition Full-Text Index
// -----------------------------------------------------------------------------
// Disease/diagnosis queries - search by name, definition, or criteria
// Example: "Find conditions with HbA1c criteria"

CREATE FULLTEXT INDEX condition_fulltext IF NOT EXISTS
FOR (c:Condition)
ON EACH [c.name, c.definition, c.diagnostic_criteria];

// Usage:
// CALL db.index.fulltext.queryNodes("condition_fulltext", "HbA1c kidney")
// YIELD node, score
// RETURN node.name, node.icd10_codes, score
// ORDER BY score DESC;

// -----------------------------------------------------------------------------
// Intervention Full-Text Index (Optional)
// -----------------------------------------------------------------------------
// Search interventions by name, description, or mechanism
// Example: "Find interventions that improve insulin sensitivity"

CREATE FULLTEXT INDEX intervention_fulltext IF NOT EXISTS
FOR (i:Intervention)
ON EACH [i.name, i.description, i.mechanism];

// Usage:
// CALL db.index.fulltext.queryNodes("intervention_fulltext", "insulin sensitivity")
// YIELD node, score
// RETURN node.name, node.type, score
// ORDER BY score DESC;

// -----------------------------------------------------------------------------
// Verification query
// -----------------------------------------------------------------------------
// Run this to verify full-text indexes were created:
// SHOW INDEXES WHERE type = "FULLTEXT";
