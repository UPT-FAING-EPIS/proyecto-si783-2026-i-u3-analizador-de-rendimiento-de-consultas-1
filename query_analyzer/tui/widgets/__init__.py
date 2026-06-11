"""TUI widgets."""

from __future__ import annotations

from query_analyzer.tui.widgets.ai_insights_panel import (
    AIInsightsPanel,
    AIObservationsPanel,
    AIRecommendationsPanel,
)
from query_analyzer.tui.widgets.diagnostic_modal import DiagnosticModal
from query_analyzer.tui.widgets.metrics_panel import MetricsPanel
from query_analyzer.tui.widgets.plan_tree_widget import PlanTreeWidget
from query_analyzer.tui.widgets.query_summary import QuerySummary

__all__ = [
    "AIInsightsPanel",
    "AIObservationsPanel",
    "AIRecommendationsPanel",
    "DiagnosticModal",
    "MetricsPanel",
    "PlanTreeWidget",
    "QuerySummary",
]
