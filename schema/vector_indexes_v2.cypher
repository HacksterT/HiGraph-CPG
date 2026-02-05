// =============================================================================
// HiGraph-CPG Schema V2 - Vector Indexes
// =============================================================================
// Vector indexes enable semantic similarity search using embeddings.
// Used for rich, natural language text where meaning matters.
//
// Model: text-embedding-3-small (OpenAI) - 1536 dimensions
// Similarity: Cosine
//
// Run with: cat schema/vector_indexes_v2.cypher | cypher-shell -u neo4j -p <password>
// Or execute in Neo4j Browser
//
// NOTE: Vector indexes may take a few minutes to become ONLINE after creation.
// Check status with: SHOW INDEXES WHERE type = "VECTOR";
// =============================================================================

// -----------------------------------------------------------------------------
// Drop existing vector indexes (if migrating)
// -----------------------------------------------------------------------------
// Uncomment if needed:
// DROP INDEX recommendation_embedding IF EXISTS;
// DROP INDEX study_embedding IF EXISTS;
// DROP INDEX keyquestion_embedding IF EXISTS;
// DROP INDEX evidencebody_embedding IF EXISTS;
// DROP INDEX clinicalmodule_embedding IF EXISTS;

// -----------------------------------------------------------------------------
// Recommendation Vector Index
// -----------------------------------------------------------------------------
// Primary clinical query surface - semantic search on recommendation text
// Example: "recommendations about kidney protection in diabetic patients"

CREATE VECTOR INDEX recommendation_embedding IF NOT EXISTS
FOR (r:Recommendation)
ON (r.embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 1536,
  `vector.similarity_function`: 'cosine'
}};

// -----------------------------------------------------------------------------
// Study Vector Index
// -----------------------------------------------------------------------------
// Rich research content - semantic search on abstracts
// Example: "studies about cardiovascular outcomes with SGLT2 inhibitors"

CREATE VECTOR INDEX study_embedding IF NOT EXISTS
FOR (s:Study)
ON (s.embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 1536,
  `vector.similarity_function`: 'cosine'
}};

// -----------------------------------------------------------------------------
// KeyQuestion Vector Index
// -----------------------------------------------------------------------------
// PICOT questions - semantic search for evidence queries
// Example: "what is known about glucose monitoring effectiveness"

CREATE VECTOR INDEX keyquestion_embedding IF NOT EXISTS
FOR (kq:KeyQuestion)
ON (kq.embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 1536,
  `vector.similarity_function`: 'cosine'
}};

// -----------------------------------------------------------------------------
// EvidenceBody Vector Index
// -----------------------------------------------------------------------------
// Synthesized conclusions - semantic search on key findings
// Example: "evidence about heart failure prevention"

CREATE VECTOR INDEX evidencebody_embedding IF NOT EXISTS
FOR (eb:EvidenceBody)
ON (eb.embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 1536,
  `vector.similarity_function`: 'cosine'
}};

// -----------------------------------------------------------------------------
// Usage Examples
// -----------------------------------------------------------------------------

// Generate embedding for a query (using GenAI plugin):
// WITH "What medications protect kidney function in diabetes?" AS query
// CALL genai.vector.encode(query, "OpenAI", {model: "text-embedding-3-small"})
// YIELD vector AS queryVector

// Semantic search on recommendations:
// CALL db.index.vector.queryNodes("recommendation_embedding", 5, queryVector)
// YIELD node, score
// RETURN node.rec_id, node.rec_text, node.strength_direction, score
// ORDER BY score DESC;

// Combined semantic + filter:
// CALL db.index.vector.queryNodes("recommendation_embedding", 10, queryVector)
// YIELD node, score
// WHERE node.strength_direction = "Strong For"
// RETURN node.rec_id, node.rec_text, score
// ORDER BY score DESC
// LIMIT 5;

// -----------------------------------------------------------------------------
// Verification query
// -----------------------------------------------------------------------------
// Run this to check vector index status:
// SHOW INDEXES WHERE type = "VECTOR"
// YIELD name, state, populationPercent
// RETURN name, state, populationPercent;

// Wait for indexes to be ONLINE before generating embeddings.
