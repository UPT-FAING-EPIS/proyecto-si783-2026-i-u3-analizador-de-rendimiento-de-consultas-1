"""Capa de API REST de FastAPI para Query Analyzer."""

from .app import app
from .router import router as analyzer_router

__all__ = ["analyzer_router", "app"]
