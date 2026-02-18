# HiGraph-CPG Deployment Runbook

This document describes the process for deploying the HiGraph-CPG clinical guideline assistant to the HacksterT environment (hackstert.cortivus.com).

## Architecture Overview

HiGraph-CPG runs as a set of Docker containers on the Windows development machine (192.168.50.185). Access is provided via an Nginx reverse proxy running on the HacksterT pilot server, which is exposed to the internet via a Cloudflare Tunnel.

```mermaid
graph TD
    User([User]) --> CF[Cloudflare Tunnel]
    CF --> Nginx[Nginx Proxy (192.168.50.150)]
    Nginx --> Landing[Landing Page Card]
    Nginx -- "/higraph-cpg" --> Streamlit[Streamlit UI (192.168.50.185:8101)]
    Streamlit --> API[FastAPI (192.168.50.185:8100)]
    API --> Neo4j[Neo4j (192.168.50.185:7687)]
```

## Prerequisites

- **HiGraph-CPG Stack**: Neo4j, API, and Streamlit containers must be running on the Windows dev machine.
- **HacksterT Stack**: Nginx, Landing Page, and Cloudflare containers must be running on the MacDevServer (or wherever HacksterT is hosted).
- **Network**: The Nginx container must be able to route traffic to `192.168.50.185`.

## Configuration Steps

### 1. HiGraph-CPG Configuration

The Streamlit application must be aware of its base URL path to handle routing correctly. This is configured in `Dockerfile.streamlit` or during `docker run`:

```bash
streamlit run app.py --server.baseUrlPath=/higraph-cpg
```

### 2. Nginx Reverse Proxy

Add the following location blocks to the Nginx configuration (typically in `conf.d/default.conf` of the HacksterT repository):

```nginx
# HiGraph-CPG Clinical Guideline Assistant
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

# Streamlit internal routes
location ^~ /higraph-cpg/_stcore {
    set $higraph_backend 192.168.50.185:8101;
    proxy_pass http://$higraph_backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
}
```

### 3. Landing Page Integration

Add the HiGraph application to the `apps` list in the landing page's main application file (`app.py`):

```python
{
    'name': 'Clinical Guideline Assistant',
    'path': '/higraph-cpg',
    'description': 'AI-powered clinical decision support for VA/DoD diabetes guidelines',
    'status': 'active',
    'icon': 'higraph-cpg-icon.svg'
}
```

Ensure the SVG icon exists at `static/images/higraph-cpg-icon.svg`.

## Startup Procedure

1. **Start HiGraph-CPG**:

   ```bash
   cd C:\Projects\va-work\HiGraph-CPG
   docker-compose up -d
   ```

2. **Start HacksterT Website**:

   ```bash
   cd C:\Projects\hacksterT-website
   docker-compose up -d --build
   ```

## Verification

1. Navigate to `https://hackstert.cortivus.com`.
2. Verify the "Clinical Guideline Assistant" card is visible.
3. Click "Launch App" and verify the Streamlit UI loads.
4. Test a sample query: *"What are the first-line pharmacotherapy recommendations for T2DM?"*
