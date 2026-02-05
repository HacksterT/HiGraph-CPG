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

- [ ] **STORY-01**: As a physician, I want the system to generate natural language answers from retrieved recommendations so that I get conversational responses with citations
  - **Priority**: Must-Have
  - **Acceptance Criteria**: (verified at Manual Testing checkpoint)
    - [ ] `POST /api/v1/answer` accepts `{"question": "...", "include_citations": true}`
    - [ ] Response includes `answer` (natural language text) and `citations` (list of rec_ids and study PMIDs)
    - [ ] Answer text references specific recommendations by ID (e.g., "According to Recommendation 22...")
    - [ ] Answer includes strength/direction context (e.g., "This is a Strong recommendation For...")
    - [ ] When no relevant results found, returns helpful message instead of hallucinating
    - [ ] Response includes `reasoning` block with generation time and token usage
    - [ ] Invalid requests return 422 with clear error messages
  - **Tasks**:
    - [ ] Backend: Create `api/services/answer_generator.py` with LLM answer synthesis
    - [ ] Backend: Create answer prompt template that includes retrieved context and citation instructions
    - [ ] Backend: Implement context window management (truncate if results exceed token limit)
    - [ ] Backend: Create `api/routers/answer.py` with `POST /api/v1/answer` endpoint
    - [ ] Backend: Create `api/models/answer.py` with AnswerRequest, AnswerResponse, Citation models
    - [ ] Backend: Add token counting and cost tracking to response metadata
    - [ ] Testing: Write tests for answer generation (with results, without results, citation format)
    - [ ] Local Testing: Test with 5 sample questions, verify citations match retrieved results
    - [ ] Manual Testing: CHECKPOINT — Verify answers are accurate, well-cited, and don't hallucinate
    - [ ] Git: Stage and commit with descriptive message
  - **Technical Notes**: Use Claude 3.5 Sonnet for answer generation (better quality than Haiku for synthesis). Prompt must instruct LLM to only use provided context, never make up recommendations. Max context ~8K tokens.
  - **Blockers**: None (depends on Part 1 query endpoint which is complete)

- [ ] **STORY-02**: As a physician, I want a chat interface so that I can have a conversation with the clinical guideline knowledge base
  - **Priority**: Must-Have
  - **Acceptance Criteria**: (verified at Manual Testing checkpoint)
    - [ ] Streamlit app runs on `localhost:8101` with chat interface
    - [ ] User can type questions in a chat input box
    - [ ] Bot responses display with markdown formatting (headers, lists, bold for rec IDs)
    - [ ] Citations appear as expandable sections below each answer
    - [ ] Chat history persists during session (scrollable conversation)
    - [ ] "Clear conversation" button resets chat history
    - [ ] Loading spinner displays while waiting for API response
    - [ ] Error messages display gracefully (API unavailable, timeout, etc.)
    - [ ] All services run in Docker containers via docker-compose
    - [ ] `docker-compose up` starts Neo4j, API, and Streamlit containers
  - **Tasks**:
    - [ ] Frontend: Create `streamlit_app/` directory structure
    - [ ] Frontend: Create `streamlit_app/app.py` with chat interface layout
    - [ ] Frontend: Implement chat message components (user bubble, bot bubble)
    - [ ] Frontend: Add expandable citation sections with study details
    - [ ] Frontend: Implement session state for chat history persistence
    - [ ] Frontend: Add loading states and error handling
    - [ ] Frontend: Style with custom CSS for clinical/professional appearance
    - [ ] Infra: Create `Dockerfile` for API service (FastAPI + uvicorn)
    - [ ] Infra: Create `Dockerfile.streamlit` for Streamlit service
    - [ ] Infra: Update `docker-compose.yml` to include api and streamlit services
    - [ ] Infra: Configure container networking (streamlit → api → neo4j)
    - [ ] Infra: Add health checks for all services
    - [ ] Infra: Create `.env.example` with all required environment variables
    - [ ] Testing: Manual testing of UI interactions (no automated Streamlit tests for MVP)
    - [ ] Local Testing: Run `docker-compose up` and test full conversation flow
    - [ ] Manual Testing: CHECKPOINT — Verify all containers start and communicate correctly
    - [ ] Git: Stage and commit with descriptive message
  - **Technical Notes**: Use `st.chat_message` for conversation UI. Store history in `st.session_state`. API calls via `httpx` to `http://api:8100` (container name). Port 8101 assigned per PORTS.md. Streamlit connects to API via Docker network, API connects to Neo4j via Docker network. External access via Cloudflare tunnel to `HackterT.cortivus.com`.
  - **Blockers**: STORY-01 must be complete (needs answer endpoint)

- [ ] **STORY-03**: As a physician, I want to see the evidence chain for any recommendation so that I can verify the supporting studies
  - **Priority**: Should-Have
  - **Acceptance Criteria**: (verified at Manual Testing checkpoint)
    - [ ] Each recommendation in the UI has a "View Evidence" button/link
    - [ ] Clicking shows: Key Question → Evidence Body → Studies list
    - [ ] Studies display: title, authors, journal, year, PMID (linked to PubMed)
    - [ ] Evidence quality rating displayed with visual indicator (High/Moderate/Low)
    - [ ] Study abstracts available in expandable sections
    - [ ] Back button returns to conversation view
  - **Tasks**:
    - [ ] Frontend: Create evidence chain component in Streamlit
    - [ ] Frontend: Implement PMID links to PubMed (https://pubmed.ncbi.nlm.nih.gov/{pmid})
    - [ ] Frontend: Add quality rating badges (color-coded)
    - [ ] Frontend: Create expandable abstract sections
    - [ ] Frontend: Wire up to `/api/v1/search/graph` with `evidence_chain_full` template
    - [ ] Testing: Manual testing of evidence chain display
    - [ ] Local Testing: Verify evidence chain for 3 different recommendations
    - [ ] Manual Testing: CHECKPOINT — Verify all studies display correctly with working PubMed links
    - [ ] Git: Stage and commit with descriptive message
  - **Technical Notes**: Use existing `evidence_chain_full` graph template. PubMed link format: `https://pubmed.ncbi.nlm.nih.gov/{pmid}`. Handle missing PMIDs gracefully.
  - **Blockers**: STORY-02 must be complete (needs base UI)

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
