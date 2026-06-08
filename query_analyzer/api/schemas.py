"""Esquemas de datos de Pydantic para la API del analizador de consultas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from query_analyzer.adapters.models import AIAnalysisResult, PlanNode


class ConnectionRequest(BaseModel):
    """Datos de conexión para el análisis."""

    engine: str = Field(..., description="Motor de BD: postgresql, mysql, sqlite, mongodb, etc.")
    host: str | None = Field(default=None, description="Host o IP del servidor")
    port: int | None = Field(default=None, description="Puerto del servidor")
    username: str | None = Field(default=None, description="Nombre de usuario")
    password: str | None = Field(default=None, description="Contraseña")
    database: str = Field(default="", description="Nombre de la base de datos o ruta de archivo")
    auth_database: str | None = Field(default=None, description="Base de datos de autenticación")
    ssl: bool = Field(default=False, description="Uso de SSL")


class AnalyzeRequest(BaseModel):
    """Petición de análisis EXPLAIN."""

    connection: ConnectionRequest
    query: str = Field(..., description="Consulta SQL/NoSQL a analizar")


class AIConfigRequest(BaseModel):
    """Configuración de IA para análisis avanzado."""

    base_url: str = Field(..., description="URL del proveedor de IA")
    api_key: str = Field(..., description="API key")
    model: str = Field(default="gpt-4o", description="Modelo a usar")


class AIAnalyzeRequest(BaseModel):
    """Petición de análisis con IA."""

    plan_json: Any = Field(..., description="Plan de ejecución (dict o string)")
    query: str = Field(..., description="Consulta original")
    engine: str = Field(..., description="Motor de BD")
    ai_config: AIConfigRequest


class MetricsRequest(BaseModel):
    """Petición de métricas del motor."""

    connection: ConnectionRequest


class SlowQueriesRequest(BaseModel):
    """Petición de consultas lentas."""

    connection: ConnectionRequest
    threshold_ms: int = Field(default=1000, ge=1, description="Umbral en ms")


class AnalyzeResponse(BaseModel):
    """Respuesta del análisis EXPLAIN."""

    success: bool
    engine: str
    query: str
    execution_time_ms: float | None = None
    plan_tree: PlanNode | None = None
    plan_summary: str | None = None
    ai_analysis: AIAnalysisResult | None = None
    analyzed_at: datetime | None = None
    raw_plan: Any = None
    metrics: dict[str, Any] = {}
    error: str | None = None


class AIAnalyzeResponse(BaseModel):
    """Respuesta del análisis con IA."""

    success: bool
    summary: str = ""
    observations: list[str] = []
    recommendations: list[str] = []
    error: str | None = None


class MetricsResponse(BaseModel):
    """Respuesta de métricas."""

    success: bool
    metrics: dict[str, Any] = {}
    error: str | None = None


class EngineInfoResponse(BaseModel):
    """Información del motor."""

    success: bool
    info: dict[str, Any] = {}
    error: str | None = None
