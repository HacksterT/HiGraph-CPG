# PRD: Demo Deployment - HiGraph-CPG on HacksterT.cortivus.com

**Status**: Complete
**Priority**: Must-Have (blocking demo)
**Estimated Effort**: 1-2 hours

## Overview

**Feature**: Deploy HiGraph-CPG Streamlit chat UI to HacksterT.cortivus.com for demonstration

**Description**: Connect the HiGraph-CPG clinical guideline assistant to the HacksterT pilot environment so it can be demonstrated to stakeholders. This involves configuring nginx reverse proxy routing and adding a card/link on the landing page.

**Problem**: The HiGraph-CPG app runs locally but isn't accessible via the HacksterT.cortivus.com domain needed for demonstrations.

**Context**: HiGraph-CPG already runs in Docker containers (Neo4j, API, Streamlit) on localhost. The HacksterT website uses nginx reverse proxy + Cloudflare tunnel for external access. We need to bridge these.

---

## Architecture

### Current State

```
HiGraph-CPG (standalone):
┌─────────────────────────────────────────┐
│ docker-compose.yml                      │
│   - Neo4j (7474, 7687)                  │
│   - API (8100)                          │
│   - Streamlit (8101) ← User-facing      │
└─────────────────────────────────────────┘

HacksterT Website:
┌─────────────────────────────────────────┐
│ docker-compose.yml                      │
│   - nginx (8090)                        │
│   - landing-page (5000)                 │
│   - cloudflared (tunnel)                │
└─────────────────────────────────────────┘
        ↓
Cloudflare Tunnel → hackstert.cortivus.com
```

### Target State

```
hackstert.cortivus.com
        ↓
Cloudflare Tunnel → nginx (8090)
        ↓
    ┌───┴───────────────────────┐
    ↓                           ↓
/higraph-cpg              / (landing page)
    ↓                           ↓
192.168.50.185:8101      landing-page:5000
(HiGraph Streamlit)      (with HiGraph card)
```

---

## Working Backlog

### STORY-01: Configure nginx reverse proxy for HiGraph-CPG

- **Priority**: Must-Have
- **Status**: ✅ COMPLETE
- **Repo**: `C:\Projects\hacksterT-website`
- **Acceptance Criteria**:
  - [x] `https://hackstert.cortivus.com/higraph-cpg` loads the Streamlit chat UI
  - [x] WebSocket connections work (required for Streamlit)
  - [x] Static assets load correctly (CSS, JS)
  - [x] Health check endpoint responds
- **Tasks**:
  - [x] Add location block for `/higraph-cpg` with WebSocket support
  - [x] Add location block for `/higraph-cpg/_stcore` for static assets
  - [x] Configure proxy headers for Streamlit compatibility
  - [x] Use variable-based routing to 192.168.50.185:8101 (Windows dev machine)
  - [x] Test locally before deploying
  - [x] Restart nginx container
- **Technical Notes**:
  - Streamlit requires WebSocket upgrade headers
  - Using direct IP (192.168.50.185:8101) since Linux Docker doesn't support host.docker.internal
  - Path: `/higraph-cpg` (with hyphen for URL consistency)
  - Added `--server.baseUrlPath=/higraph-cpg` to Dockerfile.streamlit
- **Files Modified**:
  - `C:\Projects\hacksterT-website\nginx\conf.d\default.conf`
  - `C:\Projects\va-work\HiGraph-CPG\Dockerfile.streamlit`

### STORY-02: Add HiGraph-CPG card to landing page

- **Priority**: Must-Have
- **Status**: ✅ COMPLETE
- **Repo**: `C:\Projects\hacksterT-website`
- **Acceptance Criteria**:
  - [x] Card appears on landing page with appropriate icon
  - [x] Card displays: name, description, "Launch App" button
  - [x] Clicking "Launch App" navigates to `/higraph-cpg`
  - [x] Card styling matches existing cards
- **Tasks**:
  - [x] Add HiGraph entry to `apps` list in `landing-page/app.py`
  - [x] Create SVG icon (graph nodes with medical cross)
  - [x] Place icon in `landing-page/static/images/higraph-cpg-icon.svg`
  - [x] Rebuild landing-page container
  - [x] Verify card renders correctly
- **Technical Notes**:
  - Icon is SVG (graph visualization with medical cross accent)
  - Status: 'active' (not 'coming_soon')
  - Card positioned last in list
- **Files Modified**:
  - `C:\Projects\hacksterT-website\landing-page\app.py`
  - `C:\Projects\hacksterT-website\landing-page\static\images\higraph-cpg-icon.svg` (new)

### STORY-03: Ensure HiGraph-CPG containers start with HacksterT

- **Priority**: Should-Have
- **Status**: ✅ COMPLETE (already configured)
- **Repo**: `C:\Projects\va-work\HiGraph-CPG`
- **Acceptance Criteria**:
  - [x] HiGraph containers can be started alongside HacksterT containers
  - [x] Containers restart automatically if server reboots
  - [x] Health checks pass before nginx routes traffic
- **Tasks**:
  - [x] `restart: unless-stopped` already configured for all services
  - [x] Health checks configured for neo4j, api, streamlit
  - [x] Verify containers are running before testing nginx route
  - [x] Document startup order (HiGraph first, then HacksterT, or use health checks)
  - [x] Test full restart scenario
- **Technical Notes**:
  - HiGraph runs on separate docker-compose, not merged into HacksterT
  - Both compose files can run simultaneously (different container names)
- **Files**:
  - `C:\Projects\va-work\HiGraph-CPG\docker-compose.yml` (no changes needed)

### STORY-04: Manual Testing and Documentation

- **Priority**: Must-Have
- **Status**: ✅ COMPLETE
- **Acceptance Criteria**:
  - [x] Full flow tested: landing page → card click → chat UI → ask question → get answer
  - [x] Evidence chain viewer works through proxy
  - [x] Conversation context persists during session
  - [x] Documentation updated with deployment steps
- **Tasks**:
  - [x] Test on actual hackstert.cortivus.com domain (not just localhost)
  - [x] Verify Cloudflare allow-list permits access
  - [x] Test on different browser/device
  - [x] Update project-overview.md with deployment status
  - [x] Create simple startup script or document startup steps
- **Files to Create/Modify**:
  - `C:\Projects\va-work\HiGraph-CPG\docs\deployment.md` (new)

---

## Technical Details

### Nginx Configuration (Implemented)

```nginx
# HiGraph-CPG Clinical Guideline Assistant
# Streamlit chat UI running on Windows dev machine (192.168.50.185:8101)
# Requires WebSocket support for Streamlit's real-time updates
location ^~ /higraph-cpg {
    set $higraph_backend 192.168.50.185:8101;
    proxy_pass http://$higraph_backend;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_redirect off;

    # WebSocket support (required for Streamlit)
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";

    # Long timeout for WebSocket connections
    proxy_read_timeout 86400;
    proxy_buffering off;
}

# HiGraph-CPG Streamlit static assets and internal routes
location ^~ /higraph-cpg/_stcore {
    set $higraph_backend 192.168.50.185:8101;
    proxy_pass http://$higraph_backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### Landing Page Card Entry (Implemented)

```python
{
    'name': 'Clinical Guideline Assistant',
    'path': '/higraph-cpg',
    'description': 'AI-powered clinical decision support for VA/DoD diabetes guidelines',
    'status': 'active',
    'icon': 'higraph-cpg-icon.svg'
}
```

### Streamlit Base URL Configuration (Implemented)

Added to Dockerfile.streamlit CMD:

```
--server.baseUrlPath=/higraph-cpg
```

---

## Dependencies

### Prerequisites

- HiGraph-CPG containers running (Neo4j, API, Streamlit)
- HacksterT containers running (nginx, landing, cloudflared)
- Cloudflare tunnel active
- Network connectivity between MacDevServer (192.168.50.150) and Windows dev (192.168.50.185)

### Port Assignments (per C:\Projects\PORTS.md)

- HiGraph API: 8100
- HiGraph Streamlit: 8101
- HacksterT nginx: 8090
- HacksterT landing: 5000

---

## Rollback Plan

If deployment fails:

1. Remove `/higraph-cpg` location blocks from nginx config
2. Remove card from landing page apps list
3. Restart affected containers
4. HiGraph continues running standalone on localhost:8101

---

## Success Criteria

- [x] Landing page shows HiGraph-CPG card with professional appearance
- [x] Clicking card opens chat UI at `/higraph-cpg`
- [x] Can ask clinical questions and receive answers with citations
- [x] Evidence chain viewer works (PubMed links functional)
- [x] Demo-ready for stakeholder presentation

---

## Resolved Questions

1. **Icon**: Created custom SVG icon with graph nodes and medical cross
2. **Card Position**: Last in list (user preference)
3. **Host IP**: Using 192.168.50.185:8101 (direct IP routing, since Linux Docker doesn't support host.docker.internal)

---

**Document Version**: 1.1
**Created**: February 5, 2026
**Updated**: February 5, 2026
**Related PRDs**: prd-query-api-part2.md (completed)
