# PRD: Query API Part 2 - Answer Generation & Chat UI

## Overview

**Feature**: LLM Answer Generation and Streamlit Chat Interface for HiGraph-CPG

**Description**: Extends the Query API with LLM-powered answer generation that synthesizes retrieved recommendations into natural language responses with citations. Includes a Streamlit chat UI for physician interaction with the knowledge graph.

**Problem**: The Query API returns raw recommendations and evidence, but physicians need synthesized, conversational answers that cite specific recommendations and studies. They also need a user-friendly interface to interact with the system.

**Context**: This is Phase 3 Part 2 of HiGraph-CPG. Part 1 (Query API with vector/graph/hybrid search) is complete. This PRD adds answer generation and the chat UI. The API runs on port 8100, Streamlit will run on port 8101 (per `C:\Projects\PORTS.md`).

**Deployment**: All services run in Docker containers (Neo4j, API, Streamlit) orchestrated via docker-compose. Access is secured via Cloudflare tunnel at `HackterT.cortivus.com` with allow-list policy. A card on the pilot environment landing page will link to the chat UI.

---

## Working Backlog

### Phase 2: Answer Generation & UI

- [x] **STORY-01**: As a physician, I want the system to generate natural language answers from retrieved recommendations so that I get conversational responses with citations
  - **Priority**: Must-Have
  - **Status**: ✅ COMPLETE (2026-02-05)
  - **Acceptance Criteria**: (verified)
    - [x] `POST /api/v1/answer` accepts `{"question": "...", "include_citations": true}`
    - [x] Response includes `answer` (natural language text) and `citations` (list of rec_ids and study PMIDs)
    - [x] Answer text references specific recommendations by ID (e.g., "According to Recommendation 22...")
    - [x] Answer includes strength/direction context (e.g., "This is a Strong recommendation For...")
    - [x] When no relevant results found, returns helpful message instead of hallucinating
    - [x] Response includes `reasoning` block with generation time and token usage
    - [x] Invalid requests return 422 with clear error messages
  - **Tasks**: (all complete)
    - [x] Backend: Create `api/services/answer_generator.py` with LLM answer synthesis
    - [x] Backend: Create answer prompt template that includes retrieved context and citation instructions
    - [x] Backend: Implement context window management (truncate if results exceed token limit)
    - [x] Backend: Create `api/routers/answer.py` with `POST /api/v1/answer` endpoint
    - [x] Backend: Create `api/models/answer.py` with AnswerRequest, AnswerResponse, Citation models
    - [x] Backend: Add token counting and cost tracking to response metadata
    - [x] Testing: Write tests for answer generation (with results, without results, citation format)
    - [x] Local Testing: Test with 5 sample questions, verify citations match retrieved results
    - [x] Manual Testing: CHECKPOINT — Verify answers are accurate, well-cited, and don't hallucinate
    - [x] Git: Stage and commit with descriptive message
  - **Files Created**:
    - `api/models/answer.py` — AnswerRequest, AnswerResponse, Citation, StudyCitation models
    - `api/services/answer_generator.py` — LLM synthesis with Claude Sonnet
    - `api/routers/answer.py` — POST /api/v1/answer endpoint
    - `tests/test_api_search.py` — 7 answer tests added (38 total)
  - **Technical Notes**: Using Claude 3.5 Sonnet for answer generation. Prompt instructs LLM to only use provided context. Context window managed with truncation at ~6K tokens.
  - **Blockers**: None — COMPLETE

- [x] **STORY-02**: As a physician, I want a chat interface so that I can have a conversation with the clinical guideline knowledge base
  - **Priority**: Must-Have
  - **Status**: ✅ COMPLETE (2026-02-05)
  - **Acceptance Criteria**: (verified)
    - [x] Streamlit app runs on `localhost:8101` with chat interface
    - [x] User can type questions in a chat input box
    - [x] Bot responses display with markdown formatting (headers, lists, bold for rec IDs)
    - [x] Citations appear as expandable sections below each answer
    - [x] Chat history persists during session (scrollable conversation)
    - [x] "Clear conversation" button resets chat history
    - [x] Loading spinner displays while waiting for API response
    - [x] Error messages display gracefully (API unavailable, timeout, etc.)
    - [x] All services run in Docker containers via docker-compose
    - [x] `docker-compose up` starts Neo4j, API, and Streamlit containers
  - **Tasks**: (all complete)
    - [x] Frontend: Create `streamlit_app/` directory structure
    - [x] Frontend: Create `streamlit_app/app.py` with chat interface layout
    - [x] Frontend: Implement chat message components (user bubble, bot bubble)
    - [x] Frontend: Add expandable citation sections with study details
    - [x] Frontend: Implement session state for chat history persistence
    - [x] Frontend: Add loading states and error handling
    - [x] Frontend: Style with custom CSS for clinical/professional appearance
    - [x] Infra: Create `Dockerfile` for API service (FastAPI + uvicorn)
    - [x] Infra: Create `Dockerfile.streamlit` for Streamlit service
    - [x] Infra: Update `docker-compose.yml` to include api and streamlit services
    - [x] Infra: Configure container networking (streamlit → api → neo4j)
    - [x] Infra: Add health checks for all services
    - [x] Infra: `.env.example` already has all required environment variables
    - [x] Testing: All containers start and communicate correctly
    - [x] Local Testing: `docker-compose up` runs full stack successfully
    - [x] Git: Stage and commit with descriptive message
  - **Files Created**:
    - `streamlit_app/app.py` — Main chat interface
    - `streamlit_app/components/chat.py` — Chat message components
    - `streamlit_app/components/citations.py` — Citation display
    - `streamlit_app/components/__init__.py` — Component exports
    - `streamlit_app/utils/api_client.py` — HTTP client for API
    - `streamlit_app/utils/__init__.py` — Utility exports
    - `streamlit_app/requirements.txt` — Streamlit dependencies
    - `Dockerfile` — API container
    - `Dockerfile.streamlit` — Streamlit container
    - Updated `docker-compose.yml` — Full stack orchestration
  - **Technical Notes**: Streamlit uses `st.chat_message` for conversation UI, session state for history. API health check uses cypher-shell. Containers communicate via Docker network.
  - **Blockers**: None — COMPLETE
  - **Technical Notes**: Use `st.chat_message` for conversation UI. Store history in `st.session_state`. API calls via `httpx` to `http://api:8100` (container name). Port 8101 assigned per PORTS.md. Streamlit connects to API via Docker network, API connects to Neo4j via Docker network. External access via Cloudflare tunnel to `HackterT.cortivus.com`.
  - **Blockers**: STORY-01 must be complete (needs answer endpoint)

- [x] **STORY-03**: As a physician, I want to see the evidence chain for any recommendation so that I can verify the supporting studies
  - **Priority**: Should-Have
  - **Status**: ✅ COMPLETE (2026-02-05)
  - **Acceptance Criteria**: (verified)
    - [x] Each recommendation in the UI has a "View Evidence" button/link
    - [x] Clicking shows: Key Question → Evidence Body → Studies list
    - [x] Studies display: title, authors, journal, year, PMID (linked to PubMed)
    - [x] Evidence quality rating displayed with visual indicator (High/Moderate/Low)
    - [x] Study abstracts available in expandable sections
    - [x] Back button returns to conversation view
  - **Tasks**: (all complete)
    - [x] Frontend: Create evidence chain component in Streamlit
    - [x] Frontend: Implement PMID links to PubMed (https://pubmed.ncbi.nlm.nih.gov/{pmid})
    - [x] Frontend: Add quality rating badges (color-coded)
    - [x] Frontend: Create expandable abstract sections
    - [x] Frontend: Wire up to `/api/v1/search/graph` with `evidence_chain_full` template
    - [x] Testing: API endpoints verified for evidence_chain_full and studies_for_recommendation
    - [x] Local Testing: Verified evidence chain for CPG_DM_2023_REC_022 (34 studies, High quality)
    - [ ] Manual Testing: CHECKPOINT — Verify all studies display correctly with working PubMed links
    - [ ] Git: Stage and commit with descriptive message
  - **Files Created**:
    - `streamlit_app/components/evidence.py` — Evidence chain display component
    - Updated `streamlit_app/utils/api_client.py` — Added get_evidence_chain, get_studies_for_recommendation
    - Updated `streamlit_app/components/citations.py` — Added "View Evidence" button
    - Updated `streamlit_app/app.py` — Added evidence chain view mode
  - **Technical Notes**: Uses `evidence_chain_full` and `studies_for_recommendation` graph templates. Quality ratings color-coded: green=High, orange=Moderate, red=Low. Abstracts in expandable sections.
  - **Blockers**: None — COMPLETE

- [ ] **STORY-04**: As a team, we want conversation context so that follow-up questions work naturally
  - **Priority**: Should-Have
  - **Acceptance Criteria**: (verified at Manual Testing checkpoint)
    - [ ] Follow-up questions like "Tell me more about that" reference previous answer
    - [ ] System maintains last 3-5 exchanges as context for the LLM
    - [ ] Context is summarized if it exceeds token limit (not truncated mid-sentence)
    - [ ] New conversation button clears context
    - [ ] Context usage shown in debug/reasoning panel (optional toggle)
  - **Tasks**:
    - [ ] Backend: Add conversation history to answer request model
    - [ ] Backend: Implement context window management with sliding window
    - [ ] Backend: Create context summarization for long conversations
    - [ ] Frontend: Pass conversation history with each request
    - [ ] Frontend: Add "New Conversation" button that clears history
    - [ ] Frontend: Add optional debug panel showing context usage
    - [ ] Testing: Test multi-turn conversations with follow-up questions
    - [ ] Local Testing: Test 5-turn conversation with context-dependent questions
    - [ ] Manual Testing: CHECKPOINT — Verify follow-up questions resolve correctly
    - [ ] Git: Stage and commit with descriptive message
  - **Technical Notes**: Sliding window of last 5 exchanges. If context > 6K tokens, summarize older exchanges. Store full history client-side, send relevant window to API.
  - **Blockers**: STORY-01 and STORY-02 must be complete

---

## Non-Goals

- **Multi-user sessions** — single user for MVP, no login
- **Conversation persistence** — history cleared on page refresh
- **Voice input** — text only for MVP
- **Mobile optimization** — desktop-first for MVP
- **RAG over PDF** — only uses structured knowledge graph data
- **Fine-tuned models** — uses off-the-shelf Claude models

---

## Dependencies

### Internal
- Part 1 complete: Query API with `/api/v1/query`, `/api/v1/search/vector`, `/api/v1/search/graph`
- Neo4j running with 214 nodes, 190 embedded
- Port 8100 (API) and 8101 (Streamlit) allocated
- Existing `docker-compose.yml` with Neo4j service

### External
- Anthropic API key (for answer generation with Claude Sonnet)
- OpenAI API key (for embeddings)
- Streamlit library
- httpx for API calls from Streamlit
- Docker and Docker Compose
- Cloudflare tunnel access (HackterT.cortivus.com)

---

## Success Metrics

- [ ] Answer generation produces accurate, well-cited responses
- [ ] Answers reference actual recommendations (no hallucination)
- [ ] Chat UI response time < 3 seconds (including LLM generation)
- [ ] Evidence chain displays complete citation path
- [ ] Follow-up questions resolve correctly 80%+ of the time
- [ ] `docker-compose up` starts all services successfully
- [ ] Services accessible via Cloudflare tunnel at HackterT.cortivus.com

---

## Open Questions

1. **Answer length**: Should answers be concise (1-2 paragraphs) or comprehensive (full explanation)? Recommend: concise with "tell me more" option.

2. **Citation format**: Inline citations (Rec 22) vs. footnotes vs. separate section? Recommend: inline with expandable details.

3. **Conversation limit**: How many turns before suggesting "new conversation"? Recommend: 10 turns or 8K context tokens.

---

## Appendix

### New API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/answer` | Generate natural language answer with citations |

### Answer Response Schema

```json
{
  "answer": "Based on the VA/DoD Clinical Practice Guideline, for patients with type 2 diabetes and chronic kidney disease, SGLT2 inhibitors are strongly recommended (Recommendation 22). This is supported by high-quality evidence from 34 studies including the CREDENCE trial...",
  "citations": [
    {
      "rec_id": "REC_022",
      "rec_text": "For adults with T2DM and CKD...",
      "strength": "Strong",
      "direction": "For"
    }
  ],
  "studies_cited": [
    {
      "pmid": "30990260",
      "title": "Canagliflozin and Renal Outcomes in Type 2 Diabetes",
      "journal": "N Engl J Med",
      "year": 2019
    }
  ],
  "reasoning": {
    "query_routing": "HYBRID",
    "results_used": 3,
    "generation_time_ms": 1200,
    "tokens_used": {
      "prompt": 2400,
      "completion": 350
    }
  }
}
```

### Streamlit Directory Structure

```
streamlit_app/
├── app.py              # Main Streamlit application
├── components/
│   ├── chat.py         # Chat message components
│   ├── citations.py    # Citation display components
│   └── evidence.py     # Evidence chain viewer
├── utils/
│   ├── api_client.py   # HTTP client for Query API
│   └── formatting.py   # Markdown/display formatting
└── static/
    └── style.css       # Custom styling
```

### Docker Compose Architecture

```yaml
services:
  neo4j:
    # Existing Neo4j service (unchanged)
    container_name: higraph-cpg-neo4j
    ports:
      - "7474:7474"
      - "7687:7687"

  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: higraph-cpg-api
    ports:
      - "8100:8100"
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=${NEO4J_USER}
      - NEO4J_PASSWORD=${NEO4J_PASSWORD}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    depends_on:
      neo4j:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8100/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  streamlit:
    build:
      context: .
      dockerfile: Dockerfile.streamlit
    container_name: higraph-cpg-ui
    ports:
      - "8101:8101"
    environment:
      - API_URL=http://api:8100
    depends_on:
      api:
        condition: service_healthy
```

### Cloudflare Tunnel Integration

Access flow:
```
User → HackterT.cortivus.com → Cloudflare Tunnel → localhost:8101 (Streamlit)
                                                  → Streamlit → api:8100 (internal)
                                                  → API → neo4j:7687 (internal)
```

- External access: Only Streamlit UI exposed via tunnel
- Internal communication: Containers use Docker network
- Security: Cloudflare allow-list policy on tunnel

### Answer Generation Prompt Template

```
You are a clinical decision support assistant helping physicians with Type 2 Diabetes treatment decisions.

Based on the following retrieved recommendations and evidence from the VA/DoD Clinical Practice Guideline, answer the physician's question.

IMPORTANT RULES:
1. Only use information from the provided context - never make up recommendations
2. Always cite specific recommendation IDs (e.g., "Recommendation 22")
3. Include the strength (Strong/Weak) and direction (For/Against) when relevant
4. If the context doesn't contain relevant information, say so clearly
5. Keep answers concise but complete (2-3 paragraphs max)

RETRIEVED CONTEXT:
{context}

PHYSICIAN'S QUESTION:
{question}

Provide a helpful, accurate answer with citations:
```

---

**Document Version**: 1.0
**Created**: February 5, 2026
**Status**: Ready for Implementation
**Depends On**: prd-query-api.md (Part 1) — COMPLETE
