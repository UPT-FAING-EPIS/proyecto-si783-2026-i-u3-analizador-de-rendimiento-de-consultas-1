"""Executable BDD scenarios for the database-analysis acceptance criteria."""

from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from query_analyzer.adapters import AdapterRegistry, ConnectionConfig, QueryAnalysisReport
from query_analyzer.core.connection_diagnostics import ConnectionDiagnosticsService

scenarios("query_analysis.feature")


@pytest.fixture
def context() -> dict[str, Any]:
    """Store scenario state without sharing it between examples."""
    return {}


@given("que Query Analyzer está inicializado")
def query_analyzer_is_initialized(context: dict[str, Any]) -> None:
    context["engines"] = set(AdapterRegistry.list_engines())


@when(parsers.parse('consulto si el motor "{engine}" está registrado'))
def check_registered_engine(context: dict[str, Any], engine: str) -> None:
    context["registered"] = engine in context["engines"]


@then("el motor aparece como soportado")
def engine_is_supported(context: dict[str, Any]) -> None:
    assert context["registered"] is True


@given("un reporte factual de SQLite")
def factual_sqlite_report(context: dict[str, Any]) -> None:
    context["report"] = QueryAnalysisReport(
        engine="sqlite",
        query="SELECT 1",
        execution_time_ms=0.1,
        plan_summary="Constant row",
    )


@when("serializo el reporte a JSON")
def serialize_report(context: dict[str, Any]) -> None:
    context["payload"] = context["report"].model_dump(mode="json")


@then("el reporte no contiene una puntuación universal")
def report_has_no_universal_score(context: dict[str, Any]) -> None:
    assert "score" not in context["payload"]


@then("el análisis de IA permanece ausente")
def ai_analysis_is_absent(context: dict[str, Any]) -> None:
    assert context["payload"]["ai_analysis"] is None


@given("una conexión PostgreSQL con una contraseña sensible")
def sensitive_postgres_connection(context: dict[str, Any]) -> None:
    context["secret"] = "super-secret-password"
    context["config"] = ConnectionConfig(
        engine="postgresql",
        host="localhost",
        database="query_analyzer",
        username="qa",
        password=context["secret"],
    )


@when("sanitizo un error que contiene la contraseña")
def sanitize_error(context: dict[str, Any]) -> None:
    context["safe_message"] = ConnectionDiagnosticsService.sanitize_secrets(
        f"password={context['secret']} connection failed",
        context["config"],
    )


@then("el mensaje no revela el secreto")
def secret_is_not_revealed(context: dict[str, Any]) -> None:
    assert context["secret"] not in context["safe_message"]
    assert "********" in context["safe_message"]
