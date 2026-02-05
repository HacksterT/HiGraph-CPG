"""FastAPI application for HiGraph-CPG Query API."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from api import __version__
from api.config import get_settings
from api.routers import query_router, search_router
from api.services.neo4j_service import get_neo4j_service
from api.services.query_router import get_query_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown."""
    # Startup: verify Neo4j connectivity
    neo4j = get_neo4j_service()
    if not neo4j.verify_connectivity():
        print("WARNING: Neo4j is not reachable at startup")
    else:
        print("Neo4j connection verified")

    yield

    # Shutdown: close connections
    neo4j.close()
    print("Neo4j connection closed")

    query_router_service = get_query_router()
    query_router_service.close()
    print("Query router connection closed")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        description=settings.api_description,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Cloudflare tunnel handles auth
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(search_router)
    app.include_router(query_router)

    return app


app = create_app()


@app.get(
    "/health",
    summary="Health check",
    description="Check API and database connectivity status",
    tags=["system"],
)
async def health_check():
    """
    Health check endpoint.

    Returns API status and Neo4j connectivity.
    """
    neo4j = get_neo4j_service()
    neo4j_status = "connected" if neo4j.verify_connectivity() else "disconnected"

    if neo4j_status == "disconnected":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "neo4j": neo4j_status,
                "version": __version__,
            },
        )

    return {
        "status": "ok",
        "neo4j": neo4j_status,
        "version": __version__,
    }


@app.get(
    "/",
    summary="API root",
    description="Welcome message and API info",
    tags=["system"],
)
async def root():
    """Root endpoint with API information."""
    return {
        "name": "HiGraph-CPG Query API",
        "version": __version__,
        "docs": "/docs",
        "health": "/health",
    }
