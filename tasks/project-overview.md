# HiGraph-CPG Project Overview

## Project Summary

**Project Name**: HiGraph-CPG (Hierarchical Knowledge Graph for Clinical Practice Guidelines)  
**Organization**: Department of Veterans Affairs / Department of Defense  
**Project Lead**: [Your Name]  
**Status**: Planning & Foundation Phase  
**Started**: February 4, 2026

---

## Vision

Transform clinical practice guidelines from static PDF documents into a dynamic, AI-queryable knowledge graph that enables real-time, evidence-based clinical decision support at the point of care.

---

## Problem Statement

Current clinical practice guidelines face several critical limitations:

1. **Access Friction**: Clinicians cannot quickly find relevant recommendations during patient encounters
2. **Evidence Disconnection**: The link from recommendation back to supporting studies is obscured
3. **Static Nature**: Guidelines are slow to update when new evidence emerges
4. **Query Limitations**: Cannot answer contextual questions like "What should I prescribe for THIS specific patient?"
5. **Multi-morbidity Gaps**: Difficult to reconcile recommendations across multiple disease guidelines
6. **Patient Exclusion**: Evidence-based information remains inaccessible to patients in understandable form

**Impact**: Practice variation, suboptimal care, clinician cognitive overload, delayed evidence implementation.

---

## Solution Architecture

### Core Innovation

Replace document-based guidelines with a **graph database** where:
- Clinical knowledge is represented as interconnected entities (recommendations, evidence, studies, interventions, benefits, harms)
- Relationships capture evidence chains, clinical logic, and decision reasoning
- AI agents can traverse the graph to answer natural language questions
- Updates propagate automatically through the knowledge structure

**Two ingestion paths**: The initial data load uses an automated PDF extraction pipeline (Phase 2) to bootstrap existing published guidelines into the graph. Long-term, a structured data entry portal (Phase 8) will allow guideline development teams to author content directly into the graph, eliminating PDF parsing entirely. The graph becomes the authoritative source, not a derivative of a document.

### Technology Stack

**Database**: Neo4j 5.x (graph database with native vector search)
**Deployment**: Docker containers, local development + cloud deployment via nginx/Cloudflare
**Languages**: Python 3.10+ (scripting, data ingestion, API), Cypher (graph queries)
**AI/ML**: Vector embeddings for semantic search, LLM integration for chatbot interface
**External Data**: PubMed (NIH biomedical literature database) for study metadata enrichment
**Version Control**: Git/GitHub

### Architecture Layers

```
┌─────────────────────────────────────────────────┐
│          USER INTERFACES                        │
│  Clinician Chatbot │ Patient Portal │ EHR API  │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│          APPLICATION / API LAYER                │
│  RESTful/GraphQL APIs │ Query Engine │ Auth    │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│          KNOWLEDGE GRAPH (Neo4j)                │
│  17 Node Types │ Relationships │ Vector Search  │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│          DATA INGESTION & MAINTENANCE           │
│  PDF Parser │ PubMed API │ Evidence Monitor     │
└─────────────────────────────────────────────────┘
```

---

## Schema Overview

### 17 Primary Entity Types

**Evidence & Methodology**:
1. **Guideline** - Top-level container for disease-specific CPG
2. **ClinicalModule** - Major topic areas (Pharmacotherapy, Screening, etc.)
3. **KeyQuestion** - PICOTS-based research questions
4. **EvidenceBody** - Synthesized evidence from multiple studies
5. **Study** - Individual research studies (RCTs, systematic reviews)
6. **QualityAssessment** - GRADE evaluation components
7. **DecisionFramework** - Evidence-to-recommendation reasoning

**Clinical Content**:
8. **Recommendation** - Clinical action statements
9. **ClinicalScenario** - Point-of-care decision contexts
10. **Intervention** - Treatments/therapies/actions
11. **Outcome** - Measured clinical endpoints (general)
12. **OutcomeMeasurement** - Specific study-level measurements

**Benefits & Harms** (separated for explicit risk-benefit analysis):
13. **Benefit** - Positive effects/desirable outcomes
14. **AdverseEvent** - Harms/negative effects

**Patient Factors**:
15. **PatientPopulation** - Target demographic groups
16. **PatientCharacteristic** - Specific attributes (comorbidities, risk factors)
17. **Contraindication** - Warnings/contraindications

### Key Relationship Patterns

- **Evidence Chain**: Study → EvidenceBody → Recommendation
- **Clinical Decision**: Scenario → Recommendation → Intervention
- **Benefit-Harm**: Intervention → {Produces Benefit, Causes AdverseEvent}
- **Safety**: Contraindication → Contraindicates Intervention
- **Personalization**: PatientCharacteristic → Modifies Recommendation
- **Versioning**: Recommendation(new) → Supersedes Recommendation(old)

---

## Project Phases

### Phase 1: Foundation (Current - PRD Part 1)
**Duration**: 2-3 weeks  
**Status**: In Planning

**Deliverables**:
- [ ] Neo4j Docker environment setup
- [ ] Complete schema definition with constraints/indexes
- [ ] Vector search capability configured
- [ ] Example graph traversal patterns documented
- [ ] Test data seeded for validation

**Success Criteria**:
- Neo4j running with <5s startup time
- All 17 node types created with constraints
- Vector similarity queries working
- Example traversals execute in <100ms

---

### Phase 2: Data Ingestion (Next PRD)
**Duration**: 3-4 weeks  
**Estimated Start**: After Phase 1 complete

**Scope**:
- Parse VA/DoD Type 2 Diabetes CPG PDF (165 pages)
- Extract all 54 recommendations with metadata
- Map 12 key questions with PICOTS elements
- Link 103 studies from systematic review
- Enrich studies via PubMed API (see below)
- Populate evidence bodies with GRADE assessments
- Build relationship inference with confidence scoring
- Generate embeddings for vector search

**PubMed Integration**: The CPG PDF references 103 studies but only contains basic citation text (e.g., "Smith et al., NEJM, 2019"). PubMed is the NIH's authoritative database for biomedical research, where each study has a unique identifier (PMID). The pipeline uses PubMed for two purposes:

1. **PMID Resolution** — Searches PubMed to match each parsed citation to its canonical study record, giving every Study node a globally unique identifier.
2. **Metadata Enrichment** — Fetches structured data not available in the PDF: full abstracts, MeSH terms (standardized medical subject headings), publication types, author affiliations, and DOIs.

This matters because:
- **Abstracts** get embedded as vectors on Study nodes, enabling semantic search across the evidence base (e.g., "find studies about renal outcomes with SGLT2 inhibitors").
- **MeSH terms** provide standardized vocabulary for precise filtering that free-text search cannot achieve.
- **PMIDs** make studies linkable across guidelines. When the hypertension CPG and diabetes CPG both cite the same ACCORD trial, the shared PubMed cache recognizes it as one study — critical for Phase 6 (multi-disease) cross-guideline analysis.

Without PubMed, Study nodes would contain only whatever text appeared in the PDF's reference list — incomplete, inconsistently formatted, and isolated from the broader literature.

**Key Challenges**:
- PDF parsing accuracy (tables, footnotes, references)
- PMID resolution rate (target >90% of 103 studies)
- Evidence chain linking validation
- Recommendation categorization mapping
- Quality control and SME validation

**Deliverables**:
- [ ] PDF parsing pipeline
- [ ] Data extraction scripts for each entity type
- [ ] Graph population scripts with validation
- [ ] Embedding generation pipeline
- [ ] Data quality reports
- [ ] Complete diabetes guideline in graph

**Success Metrics**:
- 100% of 54 recommendations captured
- >95% accuracy on manual validation sample
- All evidence chains complete and verified
- Vector search returns relevant results

---

### Phase 3: Query API & Interface (Future PRD)
**Duration**: 3-4 weeks  
**Estimated Start**: After Phase 2 complete

**Scope**:
- RESTful API for graph queries
- GraphQL endpoint for flexible querying
- Authentication and authorization
- Rate limiting and caching
- API documentation (OpenAPI/Swagger)
- Basic web UI for testing queries
- Query performance optimization

**Key Components**:
- Python FastAPI or Flask application
- JWT-based authentication
- Redis for caching frequent queries
- Query complexity analysis
- Logging and monitoring
- API versioning strategy

**Deliverables**:
- [ ] REST API with core endpoints
- [ ] GraphQL schema and resolver
- [ ] API authentication system
- [ ] Query optimization and caching
- [ ] API documentation
- [ ] Simple web UI for testing
- [ ] Performance benchmarks

**Success Metrics**:
- API response time <500ms for 95% of queries
- 99.9% uptime
- Comprehensive API documentation
- Load testing passes (100 concurrent users)

---

### Phase 4: Chatbot Integration (Future PRD)
**Duration**: 4-5 weeks  
**Estimated Start**: After Phase 3 complete

**Scope**:
- Natural language query understanding
- LLM integration (GPT-4, Claude, or local model)
- Context-aware response generation
- Evidence citation in responses
- Conversation memory and context tracking
- Safety guardrails for clinical responses
- User feedback collection

**Key Features**:
- "What should I prescribe for newly diagnosed T2DM?" → Retrieves relevant recommendations
- "What are the side effects of metformin?" → Lists adverse events with frequency
- "Is SGLT-2i safe with eGFR 35?" → Safety check with contraindications
- "Why is this a Strong recommendation?" → Explains GRADE reasoning
- Follow-up questions with conversation context

**Deliverables**:
- [ ] NLU pipeline for query understanding
- [ ] LLM integration for response generation
- [ ] Query → Cypher translation
- [ ] Response formatting with citations
- [ ] Conversation state management
- [ ] Clinical safety guardrails
- [ ] Chatbot UI/API
- [ ] User testing and feedback system

**Success Metrics**:
- >85% query understanding accuracy
- Response relevance score >4/5 (user ratings)
- All responses include evidence citations
- Zero unsafe/contradictory responses in testing
- <2s end-to-end response time

---

### Phase 5: Production Deployment (Future PRD)
**Duration**: 2-3 weeks  
**Estimated Start**: After Phase 4 complete

**Scope**:
- Production infrastructure setup
- Load balancing and scaling
- Backup and disaster recovery
- Monitoring and alerting
- SSL/TLS via Cloudflare
- Reverse proxy configuration (nginx)
- Security hardening
- Production data migration

**Infrastructure**:
- Docker Compose for orchestration
- Neo4j clustering (if needed for scale)
- Nginx reverse proxy
- Cloudflare for SSL and DDoS protection
- Prometheus + Grafana for monitoring
- Automated backups to cloud storage

**Deliverables**:
- [ ] Production Docker configuration
- [ ] Nginx reverse proxy setup
- [ ] Cloudflare integration
- [ ] Automated backup system
- [ ] Monitoring dashboards
- [ ] Security audit and hardening
- [ ] Production deployment runbook
- [ ] Disaster recovery procedures

**Success Metrics**:
- 99.9% uptime SLA
- <50ms additional latency from proxy
- Automated backups every 6 hours
- <15 minute recovery time objective (RTO)
- Security scan passes (no critical vulnerabilities)

---

### Phase 6: Multi-Disease Extension (Future PRD)
**Duration**: 4-6 weeks per additional disease  
**Estimated Start**: After Phase 5 complete and diabetes validated

**Scope**:
- Extend to 5-10 high-priority conditions
- Validate schema handles different disease types
- Cross-guideline interaction detection
- Shared intervention/evidence consolidation
- Multi-disease query patterns

**Priority Conditions** (VA/DoD high-impact):
1. Type 2 Diabetes Mellitus ✓ (Phase 1-5)
2. Hypertension
3. Chronic Kidney Disease
4. Heart Failure
5. COPD
6. Depression/PTSD
7. Chronic Pain Management
8. Hyperlipidemia
9. Osteoarthritis
10. Substance Use Disorder

**Per-Disease Process**:
1. Acquire latest VA/DoD CPG
2. Run ingestion pipeline (reuse Phase 2 code)
3. Clinical SME validation
4. Cross-guideline conflict identification
5. Integration testing
6. Deployment

**Deliverables** (per disease):
- [ ] Complete guideline ingested
- [ ] Clinical validation report
- [ ] Cross-guideline interaction analysis
- [ ] Updated documentation
- [ ] Performance testing with expanded graph

**Success Metrics**:
- Each disease ingest completes in <1 week
- Query performance maintained (<500ms)
- Cross-guideline queries identify conflicts
- Clinical validation >95% accuracy

---

### Phase 7: Patient-Facing Translation Layer (Future PRD)
**Duration**: 6-8 weeks  
**Estimated Start**: After Phase 6 (multiple diseases stable)

**Scope**:
- AI translation layer for patient-friendly language
- Safety guardrails for patient-facing content
- Integration with existing VA/DoD patient education materials
- Personalized education based on patient's treatment plan
- Health literacy optimization
- HIPAA compliance for patient interactions

**Key Features**:
- Same knowledge graph, different presentation layer
- "Why did my doctor prescribe metformin?" → Plain language explanation with benefits/risks
- "What are my treatment options?" → Lay summary of alternatives
- "What should I expect?" → Timeline of effects and monitoring
- Links to existing patient education resources

**Translation Principles**:
- 6th-8th grade reading level
- Avoid medical jargon or define when necessary
- Use analogies and plain language
- Emphasize actionability
- Include visual aids where helpful
- Cultural sensitivity

**Deliverables**:
- [ ] Patient query understanding (different language patterns)
- [ ] Clinical-to-lay language translation AI
- [ ] Safety content review system
- [ ] Patient education material integration
- [ ] Health literacy scoring
- [ ] Patient interface (web/mobile)
- [ ] Pilot testing with veterans
- [ ] HIPAA compliance documentation

**Success Metrics**:
- Reading level <9th grade for all responses
- >80% patient comprehension (tested)
- >90% patient satisfaction score
- Zero safety incidents in pilot
- HIPAA audit passes

---

### Phase 8: Structured Data Entry Portal (Future PRD)
**Estimated Start**: After multi-disease ingestion validates the schema across guideline types

**Context**: The PDF parsing pipeline (Phase 2) is a **bootstrapping mechanism** for ingesting existing published guidelines. Long-term, the guideline development teams who author these CPGs will enter data directly into the knowledge graph through a structured front-end portal. This eliminates PDF parsing entirely — the graph becomes the primary data store, not a derivative of a PDF.

**Scope**:
- Web-based data entry portal for guideline development teams
- Structured forms for each entity type (recommendations, key questions, evidence bodies, studies)
- GRADE methodology workflow built into the UI (strength, direction, quality ratings)
- Relationship management (link recommendations to evidence, studies to evidence bodies)
- Review and approval workflows for clinical content
- Version control and change tracking for recommendations
- Export capabilities (generate PDF/document from graph data, reversing the current flow)
- Role-based access (authors, reviewers, approvers)

**Key Insight**: This inverts the data flow. Instead of:
```
PDF document → Parse → Extract → Graph
```
It becomes:
```
Structured entry → Graph → Generate document (if needed)
```

The graph schema, validation rules, and entity relationships built in Phases 1-2 directly inform the portal's form structure and business logic. The same JSON schemas used for LLM extraction validation become the input validation rules for the data entry forms.

**Deliverables**:
- [ ] Data entry UI for all Phase 2 entity types
- [ ] GRADE methodology workflow
- [ ] Review/approval system
- [ ] Version control and audit trail
- [ ] Document generation from graph data
- [ ] Role-based access control
- [ ] Migration path from PDF-ingested data to author-maintained data

**Success Metrics**:
- Guideline teams can enter a complete CPG without any PDF intermediate step
- Data quality exceeds PDF extraction accuracy (no parsing errors possible)
- Update cycle reduced from months (PDF republish) to days (direct graph update)
- Full audit trail for every change to clinical content

---

### Phase 9: Advanced Features (Future PRDs)

**Automated Evidence Monitoring**:
- PubMed/Embase automated searches
- New study ingestion pipeline
- Impact analysis (does new evidence change recommendations?)
- Alert system for guideline developers
- Scheduled evidence review reports

**EHR Integration**:
- FHIR API for patient context
- Real-time patient data integration
- Context-aware recommendations
- Clinical decision support alerts
- Order set generation

**Quality Measurement**:
- Guideline adherence metrics
- Practice variation analysis
- Outcome tracking
- Quality improvement dashboards
- Feedback loops for guideline refinement

**Learning Healthcare System**:
- Aggregate outcomes data
- Real-world evidence integration
- Recommendation effectiveness analysis
- Continuous guideline improvement
- Research gap identification

---

## Success Metrics (Overall Project)

### Technical Metrics
- [ ] Query response time <500ms for 95% of queries
- [ ] 99.9% system uptime
- [ ] Vector search relevance >0.8 average score
- [ ] Zero data loss incidents
- [ ] <24 hour lag from evidence publication to detection

### Clinical Metrics
- [ ] Guideline-concordant prescribing rates increase 15%+
- [ ] Reduction in practice variation by 20%+
- [ ] Clinician satisfaction score >4/5
- [ ] Time to find relevant recommendation <30 seconds
- [ ] Zero patient safety incidents attributed to system

### Operational Metrics
- [ ] 5-10 guidelines fully ingested
- [ ] Time from new evidence to guideline update <30 days
- [ ] Complete evidence traceability for all recommendations
- [ ] Cross-guideline consistency checks implemented
- [ ] Automated monitoring operational

### Adoption Metrics
- [ ] 100+ active clinician users (pilot)
- [ ] 1000+ queries per week
- [ ] 50+ repeat users (high engagement)
- [ ] Clinical champion network established
- [ ] Integration with 2+ VA/DoD facilities

---

## Risk Management

### Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Graph complexity leads to slow queries | High | Medium | Index optimization, caching, query profiling early |
| PDF parsing accuracy issues | High | High | Multiple validation passes, SME review, manual correction workflow |
| Vector search quality inadequate | Medium | Medium | Test multiple embedding models, tune similarity thresholds |
| Neo4j scaling challenges | Medium | Low | Start with single instance, plan for clustering if needed |
| Data quality issues in source guidelines | High | Medium | Rigorous validation, quality metrics, SME partnership |

### Clinical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| AI generates unsafe/incorrect recommendations | Critical | Low | Safety guardrails, always cite sources, human validation layer |
| Clinicians over-rely on system | High | Medium | Training on appropriate use, emphasize clinical judgment |
| Contradictions across guidelines not detected | High | Medium | Explicit conflict detection, alert system |
| Outdated recommendations if updates lag | Medium | Medium | Automated monitoring, defined update cycles |
| Patient misinterprets information | High | Medium | Clear disclaimers, appropriate reading level, pilot testing |

### Organizational Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Lack of clinical champion buy-in | High | Medium | Early engagement, pilot programs, demonstrate value |
| Resource constraints delay progress | Medium | Medium | Phased approach, prioritize high-value features |
| Integration challenges with existing systems | Medium | Medium | Standards-based APIs, vendor-neutral approach |
| Change management resistance | Medium | High | Training, support, champions network, continuous feedback |
| Funding interruption | High | Low | Demonstrate ROI early, align with strategic priorities |

---

## Resource Requirements

### Development Team (Phase 1-5)

**Core Team**:
- Senior Software Engineer (Graph DB, Python): 1 FTE
- Data Engineer (ETL, NLP): 0.5 FTE
- ML Engineer (Embeddings, LLM integration): 0.5 FTE
- UX Designer (Chatbot interface): 0.25 FTE

**Clinical Validation**:
- Clinical SME (Physician): 0.25 FTE
- Pharmacist: 0.1 FTE
- Nurse Educator: 0.1 FTE

**Project Management**:
- Technical Project Manager: 0.25 FTE

### Infrastructure Costs

**Development** (monthly):
- Cloud hosting (AWS/Azure/GCP): $200-500
- Neo4j Enterprise (if needed): $0 (Community edition sufficient for dev)
- OpenAI API (embeddings/LLM): $100-300
- Development tools/licenses: $100

**Production** (monthly):
- Cloud hosting: $500-1500
- SSL/CDN (Cloudflare): $20-200
- Backup storage: $50-100
- Monitoring tools: $100-200
- OpenAI API (production): $300-1000

### Time Investment

**Phase 1 (Foundation)**: 120-160 hours  
**Phase 2 (Data Ingestion)**: 160-200 hours  
**Phase 3 (API)**: 160-200 hours  
**Phase 4 (Chatbot)**: 200-240 hours  
**Phase 5 (Production)**: 80-120 hours  

**Total for Diabetes MVP**: ~720-920 hours (~4.5-6 months @ 1 FTE)

---

## Dependencies & Prerequisites

### Technical Dependencies
- Docker Desktop installed and running
- Python 3.10+ development environment
- Neo4j Community Edition 5.x (via Docker)
- Git for version control
- Access to VA/DoD clinical practice guidelines (PDFs)
- PubMed API access for study metadata

### Organizational Dependencies
- Clinical SME availability for validation
- Approval for pilot deployment
- Access to target clinician users for testing
- Integration testing environment
- Security/privacy review approval

### External Dependencies
- OpenAI API access (or alternative LLM)
- Embedding model selection
- PDF parsing libraries (PyMuPDF, pdfplumber)
- Neo4j Python driver
- FastAPI or Flask framework

---

## Quality Assurance Strategy

### Data Quality
1. **Extraction Validation**: Manual review of sample (10%) of extracted recommendations
2. **Relationship Verification**: SME validation of evidence chains
3. **Completeness Checks**: Automated scripts verify all required properties present
4. **Cross-reference Validation**: PMIDs resolved, studies match citations

### Query Quality
1. **Unit Tests**: Each traversal pattern has test cases
2. **Integration Tests**: End-to-end query scenarios
3. **Performance Tests**: Load testing with concurrent users
4. **Regression Tests**: Ensure updates don't break existing queries

### Clinical Safety
1. **SME Review**: Clinical experts review all AI-generated responses
2. **Contradiction Detection**: Automated checks for conflicting recommendations
3. **Citation Verification**: All responses link back to source evidence
4. **Safety Guardrails**: System refuses unsafe queries, flags uncertainty

### User Acceptance
1. **Usability Testing**: 10+ clinicians test interface
2. **Accuracy Assessment**: Clinical experts rate response quality
3. **Satisfaction Surveys**: User feedback collection
4. **Iterative Refinement**: Continuous improvement based on feedback

---

## Documentation Strategy

### Technical Documentation
- [x] **SCHEMA.md**: Complete graph schema specification
- [x] **GRAPH_TRAVERSALS.md**: Query patterns and examples
- [ ] **NEO4J_SETUP.md**: Docker configuration and deployment
- [ ] **VECTOR_SEARCH.md**: Embedding generation and usage
- [ ] **API_SPECIFICATION.md**: REST/GraphQL endpoint documentation
- [ ] **DEPLOYMENT.md**: Production deployment procedures
- [ ] **MAINTENANCE.md**: Backup, monitoring, troubleshooting

### Process Documentation
- [ ] **DATA_INGESTION.md**: How to add new guidelines
- [ ] **VALIDATION_PROCESS.md**: Quality assurance procedures
- [ ] **UPDATE_WORKFLOW.md**: Evidence monitoring and updates
- [ ] **CLINICAL_REVIEW.md**: SME validation guidelines

### User Documentation
- [ ] **CLINICIAN_GUIDE.md**: How to use the chatbot
- [ ] **QUERY_EXAMPLES.md**: Sample questions and answers
- [ ] **INTERPRETATION_GUIDE.md**: Understanding recommendations
- [ ] **PATIENT_GUIDE.md**: Patient-facing documentation (Phase 7)

---

## Future Enhancements (Beyond Initial Phases)

### Advanced Analytics
- Practice pattern analysis
- Guideline adherence dashboards
- Outcome prediction models
- Personalized risk stratification
- Cost-effectiveness analysis

### Interoperability
- SNOMED-CT/ICD-10/RxNorm ontology mapping
- FHIR resource generation
- CDS Hooks integration
- SMART on FHIR apps
- HL7 v2 message integration

### Intelligence
- Active learning from clinician feedback
- Reinforcement learning from outcomes
- Multi-modal input (images, labs, notes)
- Explainable AI for decision support
- Uncertainty quantification

### Collaboration
- Guideline authoring tools
- Multi-stakeholder review workflows
- Version control for recommendations
- Change proposal system
- Evidence gap identification

---

## Communication Plan

### Stakeholders

**Primary**:
- Clinical leadership (VA/DoD)
- Guideline development committees
- Pilot site clinicians
- IT security/infrastructure teams

**Secondary**:
- Quality improvement teams
- Patient advocacy groups
- Research collaborators
- Vendor partners

### Touchpoints

**Weekly**: Development team standup  
**Bi-weekly**: Clinical SME review sessions  
**Monthly**: Stakeholder update presentations  
**Quarterly**: Executive steering committee  
**Ad-hoc**: User feedback sessions, demos

### Communication Channels
- Project documentation (GitHub)
- Slack/Teams channel for real-time collaboration
- Monthly newsletters to stakeholders
- Demo days for hands-on review
- Conference presentations (research dissemination)

---

## Evaluation Plan

### Pilot Study (6 months post-launch)

**Participants**: 50-100 clinicians across 2-3 VA/DoD facilities  
**Duration**: 6 months active use  
**Data Collection**:
- System usage logs (queries, response times)
- Clinical outcomes (guideline adherence, patient outcomes)
- Satisfaction surveys (monthly)
- Qualitative interviews (quarterly)
- Error reports and feedback

**Evaluation Questions**:
1. Does the system improve guideline-concordant care?
2. Do clinicians find it useful and usable?
3. Does it reduce time to find recommendations?
4. Are there any safety concerns?
5. What features are most/least valuable?

**Success Criteria for Expansion**:
- >70% clinician satisfaction
- Measurable improvement in guideline adherence
- Zero critical safety incidents
- <500ms average query response time
- >80% of users continue after 3 months

---

## Lessons Learned & Iteration

Document key learnings after each phase:

### Phase 1 (Foundation)
- [ ] What worked well in schema design?
- [ ] What would we change about the structure?
- [ ] Performance lessons from early queries?
- [ ] Docker/infrastructure issues encountered?

### Phase 2 (Data Ingestion)
- [ ] PDF parsing challenges and solutions?
- [ ] Data quality issues discovered?
- [ ] Time estimates vs actuals?
- [ ] SME validation process effectiveness?

### Future Phases
- Document after each phase completion
- Adjust subsequent plans based on learnings
- Share best practices across team
- Update documentation continuously

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-04 | [Your Name] | Initial project overview created |

---

## References

- VA/DoD Clinical Practice Guideline for Management of Type 2 Diabetes Mellitus (May 2023)
- GRADE Handbook for Grading Quality of Evidence and Strength of Recommendations
- Neo4j Graph Database Documentation
- PICOTS Framework (AHRQ)
- Clinical Decision Support Best Practices (HIMSS)

---

## Next Steps

**Immediate** (This Week):
1. Review and finalize this project overview
2. Begin Phase 1 implementation (PRD Part 1)
3. Set up development environment
4. Initial Docker/Neo4j configuration

**Short-term** (Next 2-4 Weeks):
1. Complete Phase 1 foundation
2. Validate schema with test data
3. Begin planning Phase 2 (data ingestion)
4. Recruit clinical SME for validation

**Medium-term** (Next 3-6 Months):
1. Complete Phases 1-3 (foundation, ingestion, API)
2. Initial chatbot prototype
3. Begin pilot planning
4. Identify next disease guidelines

---

**Document Owner**: [Your Name]  
**Last Updated**: February 4, 2026  
**Status**: Living Document - Update after each phase
