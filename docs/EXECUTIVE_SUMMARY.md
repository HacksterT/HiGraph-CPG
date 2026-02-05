# HiGraph-CPG: Hierarchical Knowledge Graph for Clinical Practice Guidelines

## Executive Summary

---

### Project Overview

HiGraph-CPG is a dynamic, AI-native knowledge graph architecture designed to transform how the Department of Veterans Affairs (VA) and Department of Defense (DoD) deliver evidence-based clinical decision support at the point of care. This system will serve as the foundational knowledge infrastructure for clinical practice guidelines (CPGs), beginning with the VA/DoD Type 2 Diabetes Mellitus guideline.

### The Problem

Current clinical practice guidelines, while rigorous and evidence-based, exist as static PDF documents that are:

- **Difficult to navigate** during patient encounters
- **Slow to update** when new evidence emerges
- **Hard to query** for specific clinical scenarios
- **Not integrated** with clinical decision support systems
- **Disconnected** from the underlying evidence chain

Clinicians need immediate access to the right recommendation, with supporting evidence, for their specific patient context—but today's guideline format doesn't support this need.

### The Solution

HiGraph-CPG creates a **living, queryable knowledge base** that:

1. **Structures evidence relationships** from individual studies through evidence synthesis to clinical recommendations
2. **Enables natural language queries** via AI chatbot interface for point-of-care decision support
3. **Supports dynamic updates** as new evidence emerges, with automated change detection
4. **Maintains complete traceability** from recommendation back to source studies
5. **Extends across diseases** using a common, scalable architecture
6. **Generates clinical algorithms** automatically from the knowledge graph structure

### Core Innovation

Rather than storing guidelines as documents, HiGraph-CPG represents clinical knowledge as a **graph of interconnected entities**:

- **Recommendations** linked to their supporting **Evidence Bodies**
- **Evidence Bodies** composed of individual **Studies**
- **Interventions** connected to their **Benefits** and **Adverse Events**
- **Clinical Scenarios** that trigger appropriate **Recommendations**
- **Contraindications** that modify or prevent specific treatments
- **Patient Characteristics** that influence clinical decision-making

This graph structure allows AI agents to traverse relationships and answer complex clinical questions like:

- "What should I prescribe for a T2DM patient with kidney disease and heart failure?"
- "What evidence supports using SGLT-2 inhibitors in this population?"
- "What are the contraindications I need to consider?"
- "How strong is this recommendation and why?"

### Architecture Highlights

**17 Primary Entity Types:**

- Guideline, Clinical Module, Key Question
- Evidence Body, Study, Recommendation
- Clinical Scenario, Intervention, Outcome
- Benefit, Adverse Event, Contraindication
- Patient Population, Patient Characteristic
- Quality Assessment, Decision Framework
- Plus supporting metadata entities

**Intelligent Relationship Modeling:**

- Evidence chains (Study → Evidence Body → Recommendation)
- Clinical decision flows (Scenario → Recommendation → Intervention)
- Quality/strength reasoning (Assessment → Framework → Recommendation)
- Temporal versioning (Update → Review → Supersede)

**AI-First Design:**

- Optimized for both semantic (meaning-based) and syntactic (structured) queries
- Natural language descriptions with structured properties
- Complete reasoning chains captured in the graph
- Support for vector embeddings for similarity search

### Expected Benefits

**For Veterans and Service Members (Phase 2):**

- **Patient-facing translation layer** providing evidence-based health information in plain language
- Direct access to the same clinical knowledge that guides their care, translated for lay understanding
- Integration with existing VA/DoD patient education materials through intelligent AI interpretation
- Empowered self-management through understanding of treatment rationale and evidence
- Answers to common questions like "Why did my doctor prescribe this?" or "What are my treatment options?"
- **Foundation built on clinical knowledge graph** - no separate patient content to maintain; AI translates clinical evidence with appropriate simplification and context
- Potential for personalized education materials based on individual treatment plans and characteristics

*Note: The clinical knowledge graph provides the authoritative foundation. A carefully designed AI translation layer with appropriate guardrails will render this information accessible to patients without requiring separate patient-specific content management. Existing patient education materials can be linked as supplementary resources.*

**For Clinicians:**

- Instant access to guideline-concordant recommendations via conversational AI
- Evidence-based answers tailored to specific patient characteristics
- Clear reasoning from evidence to recommendation
- Reduced cognitive load during clinical encounters

**For Clinical Leadership:**

- Real-time visibility into guideline implementation
- Ability to track when new evidence necessitates guideline updates
- Foundation for quality metrics and performance measurement
- Scalable architecture across all VA/DoD clinical domains

**For Guideline Developers:**

- Automated detection of relevant new evidence
- Simplified update process with impact analysis
- Automatic generation of clinical algorithms from knowledge structure
- Reduced time from evidence publication to guideline update

**For Healthcare System:**

- Improved adherence to evidence-based practices
- Better clinical outcomes through optimized decision support
- Reduced practice variation across facilities
- Foundation for learning healthcare system capabilities

### Initial Implementation: Type 2 Diabetes Mellitus

The VA/DoD Type 2 Diabetes CPG (May 2023) serves as the inaugural use case:

- **54 recommendations** across multiple clinical domains
- **12 key questions** with systematic evidence reviews
- **103 included studies** from comprehensive literature search
- **GRADE methodology** with full evidence-to-recommendation reasoning
- **Multiple therapeutic classes** with complex benefit-harm considerations

This diabetes guideline provides ideal complexity for validating the architecture before scaling to additional diseases.

### Technology Approach

**Graph Database Layer:**

- Primary knowledge graph storage (Neo4j or Amazon Neptune)
- Relationship traversal optimized for clinical queries
- ACID compliance for data integrity

**Vector Database Layer:**

- Semantic search capability (Pinecone/Weaviate)
- Natural language understanding of clinical concepts
- Similarity-based evidence retrieval

**API & Integration Layer:**

- RESTful and GraphQL APIs for chatbot integration
- Standardized query patterns for common clinical questions
- Authentication and audit logging for clinical use

**Update & Maintenance Layer:**

- Automated evidence monitoring agents
- Version control and change tracking
- Impact analysis for evidence updates

### Scalability & Future Vision

**Near-term (6-12 months):**

- Complete Type 2 Diabetes implementation
- Chatbot integration and pilot deployment
- Validation with VA/DoD clinicians
- Automated update workflow for one guideline

**Mid-term (1-2 years):**

- Expansion to 5-10 high-priority conditions
- **Patient-facing AI translation layer** with appropriate guardrails for direct veteran/service member access
- Integration with EHR systems for context-aware recommendations
- Development of quality measurement capabilities
- Cross-guideline interaction detection
- Linkage of existing patient education materials to knowledge graph

**Long-term (2+ years):**

- Comprehensive VA/DoD CPG knowledge base
- Ontology integration (SNOMED-CT, ICD-10, RxNorm)
- Personalized guideline adaptation based on patient data
- Learning healthcare system with feedback loops from outcomes

### Success Metrics

**Technical Metrics:**

- Query response time <500ms for 95% of clinical questions
- 99.9% uptime for production system
- <24 hour lag from evidence publication to update detection

**Clinical Metrics:**

- Guideline-concordant prescribing rates
- Time from patient encounter to decision support query
- Clinician satisfaction with decision support tool
- Reduction in practice variation

**Operational Metrics:**

- Time from new evidence to guideline update
- Number of diseases/conditions covered
- Completeness of evidence traceability
- Cross-guideline consistency checks

### Investment & Resources

**Development Phase (6 months):**

- Knowledge engineering team (2-3 FTE)
- Graph database infrastructure
- AI/ML platform for chatbot
- Clinical SME consultation time

**Maintenance Phase (ongoing):**

- Automated monitoring and update systems
- Clinical validation process
- User support and training
- Infrastructure costs

### Risk Mitigation

**Technical Risks:**

- Graph complexity → Start with single disease, validate before scaling
- Query performance → Optimize indexing and caching strategies
- Data quality → Rigorous validation and SME review process

**Clinical Risks:**

- Acceptance by clinicians → Early pilot with champion users, gather feedback
- Safety of AI recommendations → Human-in-the-loop validation, clear evidence attribution
- Integration challenges → Standard APIs, vendor-neutral approach

**Organizational Risks:**

- Resource constraints → Phased implementation, demonstrate value early
- Competing priorities → Executive sponsorship, tie to strategic initiatives
- Change management → Training, support, continuous improvement

### Why Now?

1. **Evidence-based medicine demands** are increasing as literature expands exponentially
2. **AI capabilities** for natural language understanding have matured significantly
3. **Clinical decision support** gap is well-documented as a patient safety issue
4. **VA/DoD strategic priorities** include modernization of clinical IT systems
5. **Guideline methodology (GRADE)** provides structured foundation perfect for knowledge graphs

### Conclusion

HiGraph-CPG represents a fundamental transformation in how clinical guidelines are created, maintained, and used. By structuring guideline knowledge as an AI-queryable graph rather than static documents, we enable:

- **Real-time** evidence-based decision support at the point of care
- **Dynamic** updates as medical knowledge evolves
- **Intelligent** navigation of complex clinical scenarios
- **Scalable** architecture across all clinical domains

The VA/DoD Type 2 Diabetes guideline provides the perfect starting point to validate this approach, with immediate clinical impact for one of the highest-priority chronic diseases in the veteran and service member populations.

This is not just a better way to publish guidelines—it's the foundation for a learning healthcare system that continuously improves clinical care through better knowledge management.

---

**Document Version:** 1.0  
**Date:** February 4, 2026  
**Project Lead:** [Your Name]  
**Contact:** [Contact Information]
