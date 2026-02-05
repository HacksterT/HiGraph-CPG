"""API routers for different endpoint groups."""

from api.routers.answer import router as answer_router
from api.routers.query import router as query_router
from api.routers.search import router as search_router

__all__ = ["search_router", "query_router", "answer_router"]
