"""FastAPI application for Query Analyzer."""

import uvicorn
from fastapi import FastAPI

from query_analyzer import __version__
from query_analyzer.api.router import router

app = FastAPI(
    title="Query Analyzer API",
    description="API REST para obtener planes y métricas factuales de consultas.",
    version=__version__,
)
app.include_router(router, prefix="/api/v1")


def main() -> None:
    """Run the API server on the local development address."""
    uvicorn.run("query_analyzer.api.app:app", host="127.0.0.1", port=8001)


if __name__ == "__main__":
    main()
