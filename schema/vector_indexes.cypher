// HiGraph-CPG Vector Indexes
// For semantic similarity search using OpenAI text-embedding-3-small (1536 dimensions)

// Recommendation text similarity
CREATE VECTOR INDEX recommendation_embedding IF NOT EXISTS
FOR (r:Recommendation) ON (r.embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 1536,
  `vector.similarity_function`: 'cosine'
}};

// Clinical scenario similarity
CREATE VECTOR INDEX scenario_embedding IF NOT EXISTS
FOR (cs:ClinicalScenario) ON (cs.embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 1536,
  `vector.similarity_function`: 'cosine'
}};

// Intervention description similarity
CREATE VECTOR INDEX intervention_embedding IF NOT EXISTS
FOR (i:Intervention) ON (i.embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 1536,
  `vector.similarity_function`: 'cosine'
}};
