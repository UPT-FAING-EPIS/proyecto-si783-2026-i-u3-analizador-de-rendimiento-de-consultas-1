"""Servidor temporal para probar la API del analizador aisladamente."""

import uvicorn
from fastapi import FastAPI

from query_analyzer.api.router import router

app = FastAPI(title="Query Analyzer API (Test)")
app.include_router(router, prefix="/api/v1")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
