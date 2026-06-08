"""Endpoints de la API FastAPI para el analizador de consultas."""

from typing import Any

from fastapi import APIRouter

from query_analyzer.adapters import AdapterRegistry
from query_analyzer.adapters.models import ConnectionConfig
from query_analyzer.core import AIAnalyzer

from .schemas import (
    AIAnalyzeRequest,
    AIAnalyzeResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    ConnectionRequest,
    EngineInfoResponse,
    MetricsRequest,
    MetricsResponse,
    SlowQueriesRequest,
)

router = APIRouter(prefix="/analyzer", tags=["Query Analyzer"])


def _build_config(conn: ConnectionRequest) -> ConnectionConfig:
    """Convierte el schema de API a ConnectionConfig del core."""
    extra: dict[str, Any] = {}
    if conn.auth_database:
        extra["authSource"] = conn.auth_database
    if conn.ssl:
        extra["ssl"] = conn.ssl

    return ConnectionConfig(
        engine=conn.engine,
        host=conn.host,
        port=conn.port,
        username=conn.username,
        password=conn.password,
        database=conn.database,
        extra=extra,
    )


@router.get("/engines")
def list_engines() -> dict[str, list[str]]:
    """Lista todos los motores de BD soportados."""
    return {"engines": AdapterRegistry.list_engines()}


@router.post("/explain", response_model=AnalyzeResponse)
def analyze_query(req: AnalyzeRequest) -> AnalyzeResponse:
    """Ejecuta EXPLAIN en una consulta y retorna el análisis."""
    try:
        config = _build_config(req.connection)
        adapter = AdapterRegistry.create(req.connection.engine, config)

        with adapter:
            report = adapter.execute_explain(req.query)

        return AnalyzeResponse(
            success=True,
            engine=req.connection.engine,
            query=req.query,
            execution_time_ms=report.execution_time_ms,
            plan_tree=report.plan_tree,
            plan_summary=report.plan_summary,
            ai_analysis=report.ai_analysis,
            analyzed_at=report.analyzed_at,
            raw_plan=report.raw_plan,
            metrics=report.metrics,
        )
    except Exception as e:
        return AnalyzeResponse(
            success=False,
            engine=req.connection.engine,
            query=req.query,
            error=str(e),
        )


@router.post("/ai", response_model=AIAnalyzeResponse)
def ai_analyze(req: AIAnalyzeRequest) -> AIAnalyzeResponse:
    """Analiza un plan EXPLAIN usando IA."""
    try:
        analyzer = AIAnalyzer(
            base_url=req.ai_config.base_url,
            api_key=req.ai_config.api_key,
            model=req.ai_config.model,
        )

        if not analyzer.available:
            return AIAnalyzeResponse(success=False, error="IA no configurada correctamente")

        result = analyzer.analyze(req.plan_json, req.query, req.engine)

        if result is None:
            return AIAnalyzeResponse(success=False, error="Sin respuesta de IA")

        return AIAnalyzeResponse(
            success=True,
            summary=result.summary,
            observations=result.observations,
            recommendations=result.recommendations,
        )
    except Exception as e:
        return AIAnalyzeResponse(success=False, error=str(e))


@router.post("/metrics", response_model=MetricsResponse)
def get_metrics(req: MetricsRequest) -> MetricsResponse:
    """Obtiene métricas del motor de BD."""
    try:
        config = _build_config(req.connection)
        adapter = AdapterRegistry.create(req.connection.engine, config)

        with adapter:
            metrics = adapter.get_metrics()

        return MetricsResponse(success=True, metrics=metrics)
    except Exception as e:
        return MetricsResponse(success=False, error=str(e))


@router.post("/slow-queries")
def get_slow_queries(req: SlowQueriesRequest) -> dict[str, Any]:
    """Obtiene las consultas lentas del motor."""
    try:
        config = _build_config(req.connection)
        adapter = AdapterRegistry.create(req.connection.engine, config)

        with adapter:
            queries = adapter.get_slow_queries(req.threshold_ms)

        return {"success": True, "slow_queries": queries}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/engine-info", response_model=EngineInfoResponse)
def get_engine_info(req: MetricsRequest) -> EngineInfoResponse:
    """Obtiene información del motor (versión, config, etc.)."""
    try:
        config = _build_config(req.connection)
        adapter = AdapterRegistry.create(req.connection.engine, config)

        with adapter:
            info = adapter.get_engine_info()

        return EngineInfoResponse(success=True, info=info)
    except Exception as e:
        return EngineInfoResponse(success=False, error=str(e))
