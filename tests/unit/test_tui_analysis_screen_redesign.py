"""Unit tests for the redesigned TUI Analysis Screen and widgets (Plan 02)."""

from __future__ import annotations

import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from query_analyzer.adapters.models import (
    AIAnalysisResult,
    PlanNode,
    QueryAnalysisReport,
)
from query_analyzer.tui.screens.analysis_screen import AnalysisScreen
from query_analyzer.tui.widgets.ai_insights_panel import AIInsightsPanel
from query_analyzer.tui.widgets.metrics_panel import MetricsPanel
from query_analyzer.tui.widgets.plan_tree_widget import PlanTreeWidget
from query_analyzer.tui.widgets.query_editor import QueryEditor
from query_analyzer.tui.widgets.query_summary import QuerySummary

# ═══════════════════════════════════════════════════════════════
# ANALYSIS SCREEN & KEYBOARD BINDINGS TESTS
# ═══════════════════════════════════════════════════════════════


def test_bindings_mapping_updates() -> None:
    """Verify that bindings for copy ('c'), focus editor ('e'), and export ('x') exist."""
    all_bindings = {(b.key, b.action) for b in AnalysisScreen.BINDINGS}
    assert ("c", "copy_query") in all_bindings
    assert ("e", "focus_editor") in all_bindings
    assert ("x", "export") in all_bindings


def test_action_focus_editor(monkeypatch) -> None:
    """Verify focus_editor action invokes focus_editor on QueryEditor."""
    screen = AnalysisScreen("demo")
    editor_mock = MagicMock()

    # Mock query_one to return editor_mock
    monkeypatch.setattr(screen, "query_one", lambda widget_cls: editor_mock)

    screen.action_focus_editor()
    editor_mock.focus_editor.assert_called_once()


def test_action_copy_query(monkeypatch) -> None:
    """Verify copy_query action copies query text using app.copy_to_clipboard."""
    screen = AnalysisScreen("demo")

    # Mock query_one for QueryEditor
    editor_mock = SimpleNamespace(query_text="SELECT * FROM my_table")
    monkeypatch.setattr(screen, "query_one", lambda widget_cls: editor_mock)

    # Mock app clipboard
    copied = []
    fake_app = SimpleNamespace(
        copy_to_clipboard=lambda text: copied.append(text), notify=lambda msg: None
    )
    monkeypatch.setattr(AnalysisScreen, "app", property(lambda _self: fake_app))

    screen.action_copy_query()
    assert copied == ["SELECT * FROM my_table"]


# ═══════════════════════════════════════════════════════════════
# WIDGET: QUERYSUMMARY TESTS
# ═══════════════════════════════════════════════════════════════


def test_query_summary_render_and_copy(monkeypatch) -> None:
    """Test redesigned QuerySummary rendering of context, SQL, and copy button press."""
    widget = QuerySummary()

    # Mock child elements
    context_mock = MagicMock()
    plan_mock = MagicMock()
    sql_mock = MagicMock()

    def mock_query_one(selector, widget_cls=None):
        if selector == "#summary-context":
            return context_mock
        if selector == "#summary-plan":
            return plan_mock
        if selector == "#summary-sql":
            return sql_mock
        raise KeyError(selector)

    monkeypatch.setattr(widget, "query_one", mock_query_one)

    # Build a fake report
    report = QueryAnalysisReport(
        engine="postgresql",
        query="SELECT 1",
        execution_time_ms=12.34,
        plan_summary="Index Scan on test",
        analyzed_at=datetime.datetime(2026, 6, 10, 15, 0, 0, tzinfo=datetime.UTC),
    )

    widget.render_summary("SELECT 1", report, "postgres_prod")

    # Verify context info formatting
    context_call_arg = context_mock.update.call_args[0][0]
    assert "postgres_prod" in context_call_arg
    assert "POSTGRESQL" in context_call_arg
    assert "12.34 ms" in context_call_arg
    assert "2026-06-10" in context_call_arg

    # Verify plan summary formatting
    plan_mock.update.assert_called_once()
    assert "Index Scan on test" in plan_mock.update.call_args[0][0]

    # Verify SQL syntax highlighting box update
    sql_mock.update.assert_called_once()

    # Test copy button pressed
    copied = []
    fake_app = SimpleNamespace(
        copy_to_clipboard=lambda text: copied.append(text), notify=lambda msg: None
    )
    monkeypatch.setattr(QuerySummary, "app", property(lambda _self: fake_app))

    event_mock = SimpleNamespace(button=SimpleNamespace(id="btn-copy-query"))
    widget.on_button_pressed(event_mock)
    assert copied == ["SELECT 1"]


# ═══════════════════════════════════════════════════════════════
# WIDGET: PLANTREEWIDGET TESTS
# ═══════════════════════════════════════════════════════════════


def test_plan_tree_widget_neutral_coloration(monkeypatch) -> None:
    """Test PlanTreeWidget uses neutral cyan color for execution time."""
    node = PlanNode(node_type="Seq Scan", actual_time_ms=15.67)

    formatted = PlanTreeWidget._format_node_line(node)

    # No red/green/yellow coloration, must be neutral cyan
    assert "[cyan]15.67ms[/cyan]" in formatted
    assert "[red]" not in formatted
    assert "[green]" not in formatted
    assert "[yellow]" not in formatted


def test_plan_tree_widget_raw_plan_fallback(monkeypatch) -> None:
    """Test PlanTreeWidget falls back to raw_plan json syntax when plan_tree is None."""
    widget = PlanTreeWidget()
    content_mock = MagicMock()
    monkeypatch.setattr(widget, "query_one", lambda selector, widget_cls=None: content_mock)

    raw = {"stage": "COLLSCAN", "docs": 100}
    widget.render_plan(None, raw)

    # Must update plan-content using a syntax-highlighted json representation
    content_mock.update.assert_called_once()
    syntax_arg = content_mock.update.call_args[0][0]
    assert syntax_arg.__class__.__name__ == "Syntax"
    assert syntax_arg.lexer.name == "JSON"


# ═══════════════════════════════════════════════════════════════
# WIDGET: AIINSIGHTSPANEL TESTS
# ═══════════════════════════════════════════════════════════════


def test_ai_insights_panel_disabled_state(monkeypatch) -> None:
    """Verify State A: AI is not configured (ai_analysis is None, ai_error is None)."""
    panel = AIInsightsPanel()
    content_mock = MagicMock()
    monkeypatch.setattr(panel, "query_one", lambda selector, widget_cls=None: content_mock)

    panel.render_ai_analysis(None, None)

    content_mock.update.assert_called_once()
    assert "AI no configurada" in content_mock.update.call_args[0][0]


def test_ai_insights_panel_failed_state(monkeypatch) -> None:
    """Verify State B: AI API call failed (ai_error is populated)."""
    panel = AIInsightsPanel()
    content_mock = MagicMock()
    monkeypatch.setattr(panel, "query_one", lambda selector, widget_cls=None: content_mock)

    panel.render_ai_analysis(None, "HTTP 500: Internal Server Error")

    content_mock.update.assert_called_once()
    assert "Error en la consulta de IA" in content_mock.update.call_args[0][0]
    assert "HTTP 500" in content_mock.update.call_args[0][0]


def test_ai_insights_panel_no_emojis_in_observations(monkeypatch) -> None:
    """Verify State C: AI is successful and observations do not use emojis."""
    panel = AIInsightsPanel()
    content_mock = MagicMock()
    monkeypatch.setattr(panel, "query_one", lambda selector, widget_cls=None: content_mock)

    ai_res = AIAnalysisResult(
        summary="Plan seems fine",
        observations=[
            "CRITICAL: seq scan on big table",
            "HIGH: missing index",
            "MEDIUM: sort exceeds buffer",
            "LOW: minor check",
        ],
        recommendations=[],
    )

    panel.render_ai_analysis(ai_res, None)

    content_mock.update.assert_called_once()
    rendered_text = content_mock.update.call_args[0][0]

    # Must use standard tag prefixes, not emojis
    assert "[CRITICO]" in rendered_text
    assert "[ALTO]" in rendered_text
    assert "[MEDIO]" in rendered_text
    assert "[INFO]" in rendered_text
    assert "⚠️" not in rendered_text
    assert "▲" not in rendered_text
    assert "ℹ️" not in rendered_text


# ═══════════════════════════════════════════════════════════════
# ADDITIONAL OBLIGATORY REDESIGN TESTS
# ═══════════════════════════════════════════════════════════════


def test_metrics_panel_formatting_and_flattening() -> None:
    """Test metrics panel formatting and flattening of nested dicts/lists, sorting, and neutral colors."""
    panel = MetricsPanel()
    content_mock = MagicMock()

    # Mock query_one
    panel.query_one = lambda selector, widget_cls=None: content_mock

    observed_metrics = {
        "b_metric": 0,
        "a_metric": False,
        "c_metric": "",
        "d_metric": None,
        "nested": {"y": 10, "x": [1, {"nested_in_list": "value"}]},
    }

    panel.render_metrics(12.34, None, observed_metrics)

    content_mock.update.assert_called_once()
    rendered = content_mock.update.call_args[0][0]

    # Assert values are formatted and clearly differentiable
    assert "a_metric: [cyan]False[/cyan]" in rendered
    assert "b_metric: [cyan]0[/cyan]" in rendered
    assert 'c_metric: [cyan]"" (cadena vacía)[/cyan]' in rendered
    assert "d_metric: [cyan]No disponible[/cyan]" in rendered

    # Assert nested dicts and lists are flattened with dot and index notation
    assert "nested.y: [cyan]10[/cyan]" in rendered
    assert "nested.x[0]: [cyan]1[/cyan]" in rendered
    assert "nested.x[1].nested_in_list: [cyan]value[/cyan]" in rendered

    # Assert sorted order: key order should be a_metric, b_metric, c_metric, d_metric, nested...
    lines = [line for line in rendered.split("\n") if ": [cyan]" in line]
    keys = [line.split(":")[0].strip() for line in lines]

    # Engine metrics part starts after "Engine metrics" header
    engine_metrics_keys = keys[3:]  # skip exec time, rows examined, rows returned
    assert engine_metrics_keys == sorted(engine_metrics_keys)


def test_negative_search_for_subjective_terms() -> None:
    """Verify negative search for 'score', 'warning', 'recommendation' in factual panels."""
    # Test QuerySummary
    widget_summary = QuerySummary()
    summary_mock = MagicMock()
    widget_summary.query_one = lambda selector, widget_cls=None: summary_mock

    report = QueryAnalysisReport(
        engine="postgresql",
        query="SELECT 1",
        execution_time_ms=10.0,
        plan_summary="Index Scan",
    )
    widget_summary.render_summary("SELECT 1", report, "postgres")

    for arg in summary_mock.update.call_args_list:
        val = arg[0][0]
        text = val.code.lower() if hasattr(val, "code") else str(val).lower()
        assert "score" not in text
        assert "warning" not in text
        assert "recommendation" not in text
        assert "recomendación" not in text
        assert "advertencia" not in text

    # Test MetricsPanel
    widget_metrics = MetricsPanel()
    metrics_mock = MagicMock()
    widget_metrics.query_one = lambda selector, widget_cls=None: metrics_mock

    widget_metrics.render_metrics(10.0, None, {})
    rendered_metrics = metrics_mock.update.call_args[0][0].lower()
    assert "score" not in rendered_metrics
    assert "warning" not in rendered_metrics
    assert "recommendation" not in rendered_metrics


def test_plan_tree_rendering_error_fallback(monkeypatch) -> None:
    """Verify fallback to raw_plan when PlanTreeWidget throws exception during tree rendering."""
    widget = PlanTreeWidget()
    content_mock = MagicMock()
    monkeypatch.setattr(widget, "query_one", lambda selector, widget_cls=None: content_mock)

    # Simulate exception inside tree generation by mocking a broken PlanNode
    broken_node = MagicMock()

    def raise_err(self):
        raise Exception("Broken node structure")

    # Accessing node_type will raise exception
    type(broken_node).node_type = property(raise_err)

    raw = {"stage": "IXSCAN"}
    widget.render_plan(broken_node, raw)

    # Should fall back to render_plan using raw plan JSON
    content_mock.update.assert_called_once()
    syntax_arg = content_mock.update.call_args[0][0]
    assert syntax_arg.__class__.__name__ == "Syntax"


def test_state_transitions(monkeypatch) -> None:
    """Test transitions of screen states: idle, connecting, analyzing, success, error."""
    screen = AnalysisScreen("postgres_prod")

    analyze_btn = MagicMock()
    clear_btn = MagicMock()
    hist_btn = MagicMock()
    export_btn = MagicMock()
    editor = MagicMock()
    status_static = MagicMock()
    query_summary = MagicMock()
    metrics_panel = MagicMock()
    plan_tree_widget = MagicMock()
    ai_insights_panel = MagicMock()

    def mock_query_one(selector, widget_cls=None):
        if selector == "#btn-analyze":
            return analyze_btn
        if selector == "#btn-clear":
            return clear_btn
        if selector == "#btn-history":
            return hist_btn
        if selector == "#btn-export":
            return export_btn
        if selector == "#run-status":
            return status_static
        if selector == QueryEditor or (
            isinstance(selector, type) and issubclass(selector, QueryEditor)
        ):
            return editor
        if selector == QuerySummary or (
            isinstance(selector, type) and issubclass(selector, QuerySummary)
        ):
            return query_summary
        if selector == MetricsPanel or (
            isinstance(selector, type) and issubclass(selector, MetricsPanel)
        ):
            return metrics_panel
        if selector == PlanTreeWidget or (
            isinstance(selector, type) and issubclass(selector, PlanTreeWidget)
        ):
            return plan_tree_widget
        if selector == AIInsightsPanel or (
            isinstance(selector, type) and issubclass(selector, AIInsightsPanel)
        ):
            return ai_insights_panel
        raise KeyError(selector)

    monkeypatch.setattr(screen, "query_one", mock_query_one)
    monkeypatch.setattr(screen, "run_analysis_worker", lambda text: None)

    # 1. Trigger analysis (transition: analyzing)
    editor.query_text = "SELECT 1"
    screen._trigger_analysis("SELECT 1")

    editor.set_busy.assert_called_with(True)
    assert analyze_btn.disabled is True
    assert "Analizando..." in status_static.update.call_args[0][0]

    # 2. Success (transition: success)
    report = QueryAnalysisReport(
        engine="postgresql",
        query="SELECT 1",
        execution_time_ms=1.5,
        plan_summary="Index Scan",
    )

    # Mock history and rendering
    monkeypatch.setattr(
        "query_analyzer.tui.screens.analysis_screen.get_history_manager", lambda: MagicMock()
    )
    monkeypatch.setattr(screen, "_render_report", lambda *args: None)

    screen._on_analysis_success("SELECT 1", report)
    editor.set_busy.assert_called_with(False)
    assert analyze_btn.disabled is False
    assert "Análisis completado" in status_static.update.call_args[0][0]

    # 3. Error (transition: analysis_error)
    screen._on_analysis_error("Query syntax error")
    editor.set_busy.assert_called_with(False)
    assert analyze_btn.disabled is False
    assert "Error: Query syntax error" in status_static.update.call_args[0][0]


def test_double_execution_prevention(monkeypatch) -> None:
    """Verify double execution prevention via exclusive work annotation."""
    screen = AnalysisScreen("postgres_prod")

    # Mock self.run_worker
    run_worker_mock = MagicMock()
    monkeypatch.setattr(screen, "run_worker", run_worker_mock)

    # Call the decorated worker method
    screen.run_analysis_worker("SELECT 1")

    # Assert run_worker was called with exclusive=True
    run_worker_mock.assert_called_once()
    kwargs = run_worker_mock.call_args[1]
    assert kwargs.get("exclusive") is True
    assert kwargs.get("thread") is True


def test_long_query_rendering(monkeypatch) -> None:
    """Verify long query rendering handles 5,000 characters without crashing."""
    widget = QuerySummary()
    context_mock = MagicMock()
    plan_mock = MagicMock()
    sql_mock = MagicMock()

    def mock_query_one(selector, widget_cls=None):
        if selector == "#summary-context":
            return context_mock
        if selector == "#summary-plan":
            return plan_mock
        if selector == "#summary-sql":
            return sql_mock
        raise KeyError(selector)

    monkeypatch.setattr(widget, "query_one", mock_query_one)

    long_query = "SELECT " + ",".join([f"column_{i}" for i in range(1000)])
    assert len(long_query) > 5000

    report = QueryAnalysisReport(
        engine="postgresql",
        query=long_query,
        execution_time_ms=50.0,
        plan_summary="Select all",
    )

    # Should render successfully without raising layout exception
    widget.render_summary(long_query, report, "postgres")
    sql_mock.update.assert_called_once()
