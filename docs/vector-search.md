# Vector Searching

## What is Vector Searching?

Vector searching transforms clinical text (like a recommendation or symptom) into a mathematical "map" where meanings are stored as coordinates. Instead of searching for exact keywords like a traditional search engine, it searches for **semantic neighborhoods**.

> [!NOTE]
> **Analogy**: Traditional search is like looking for a book by its exact title; Vector search is like asking a librarian for "something about heart health" and being led to the right section, even if the books there don't have the word "heart" in the title.

## What it adds to HiGraph-CPG

- **Semantic Retrieval**: Clinicians can query using natural language (e.g., *"How do I manage high blood sugar?"*) and the system will find relevant guidelines for *"Glucose management"* or *"HbA1c targets"* because it understands they are semantically related.
- **Bridges Graph and Text**: It connects the structured clinical nodes (the "Graph") with the nuance of human language (the "Vector"). This allows the system to handle the complexity and variation in how medical concepts are described across different guidelines.
- **Foundation for Clinical AI**: This is the "brain" that allows a future AI assistant (LLM) to accurately find and pull the right evidence from the database to answer complex clinical questions without missing context.

## Technical Details: What exactly is vectorized?

In HiGraph-CPG, we vectorize **specific node properties** rather than relationships or entire neighborhoods.

### Targets & Practical Examples

Here is exactly what the system "sees" and turns into a vector using the **OpenAI `text-embedding-3-small`** model:

| Entity Type | Property Vectorized | Practical Example from Dataset |
| :--- | :--- | :--- |
| **Recommendation** | `rec_text` | *"In adults with newly diagnosed T2DM, we recommend metformin as first-line pharmacotherapy in addition to lifestyle modifications."* |
| **Study** | `title` or `abstract` | *"Effect of intensive blood-glucose control with metformin on complications in overweight patients with type 2 diabetes (UKPDS 34)"* |
| **Key Question** | `question_text` | *"In adults with T2DM, what is the comparative effectiveness of pharmacologic interventions?"* |
| **Evidence Body** | `key_findings` | *"Metformin reduces HbA1c by 1.5% vs placebo with low risk of hypoglycemia and neutral/beneficial weight effects"* |

- **Relationships**: These are **not** vectorized. We use Cypher to traverse these structural connections after the vector search provides an entry point.
- **Neighborhoods**: We don't vectorize neighborhoods as a unit. Vector search finds the "start node" based on the text above, and the Graph Database provides the "context" by exploring its neighbors.

## How it Works (Gen AI & OpenAI)

- **Model**: OpenAI’s `text-embedding-3-small` (1,536-dimensional vectors).
- **Orchestration**: Handled by the **Neo4j GenAI plugin**.
- **Process**:
    1. The plugin extracts text from the node property.
    2. It sends the text to OpenAI to generate the embedding.
    3. The resulting vector is stored directly on the node in an `embedding` property.
    4. A **Vector Index** (using Cosine similarity) is used to find the most relevant nodes in milliseconds.

## Next Steps: Advanced Embedding Strategy

While the current architecture provides a robust baseline using **semantic NLP**, the roadmap involves moving toward a **Deep Graph Embedding** model that is contextually aware of the graph's structure.

### Comparative Strategy

| Feature | Baseline (Current) | Advanced (Roadmap) |
| :--- | :--- | :--- |
| **Primary Model** | OpenAI `text-embedding-3-small` | OpenAI `text-embedding-3-Large` + PyKEEN (Rotate) |
| **Logic Focus** | **NLP-First**: Semantic meaning of text. | **Topology-First**: Structural meaning of triples. |
| **Context** | **Isolated**: Node is embedded in vacuum. | **Augmented**: First layer uses neighborhood text. |
| **Relationship Handling** | Traversed via Cypher *after* search. | Encoded natively into the vector space. |
| **Infrastructure** | Neo4j GenAI Plugin | Multi-layer Custom Pipeline (KGE) |

### Why This Matters: The Move to Cosmos DB

As the infrastructure migrates from Native Graph (Neo4j) to **Graph-on-Document (Cosmos DB)**, the two-layer strategy becomes critical for performance and reliability:

1. **Synthetic Re-assembly**: Cosmos DB stores nodes and edges as discrete JSON documents (shredded data). The **KGE/Rotate layer** "re-assembles" these connections mathematically within the vector, ensuring related entities are geographically close in the vector space even if they are physically partitioned.
2. **Reducing Traversal Latency**: By encoding the "shape" of relationships into the vector, we can find "neighborhood points" instantly. This reduces the number of Gremlin traversals (hops) required to find the full clinical context.
3. **Structural Stability**: In a schemaless document environment, the KGE layer acts as a **geometric blueprint**, ensuring that search results are ranked based on the underlying clinical hierarchy (triples) rather than just keyword density.

### The 99% Accuracy Target: SME-Led Ingestion

To achieve clinical-grade reliability (99%+ accuracy), the project utilizes **SME-led manual ingestion** instead of automated PDF parsing. This transforms the system's capabilities:

- **From Parsing to Replication**: By having professionals enter the data, we eliminate "hallucinated" structures. The KGE layer no longer hashes "noisy" code; it encodes **pure clinical intent**.
- **Double-Injection of Intelligence**: Logic is injected twice—once by the experts during data entry, and once by the KGE model during vectorization. This creates a "Knowledge Replication Engine" where the vector space precisely mirrors the expert's logical framework.
- **Eliminating the 'Ambiguity Ceiling'**: While NLP alone hits a ceiling at 85-90%, the addition of a topology-aware KGE layer allows the system to differentiate between nodes that sound similar but play different functional roles in a patient's care journey.

> [!TIP]
> **Summary**: The Advanced approach moves away from just finding "similar words" and starts finding "similar roles in the clinical workflow." By using a two-layer model, we move the "intelligence" of the graph into the embedding itself, mitigating the overhead of document-based traversals.
