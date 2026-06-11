"""Tests for the factual query report contract."""

from datetime import UTC, datetime

import pytest

from query_analyzer.adapters.models import AIAnalysisResult, PlanNode, QueryAnalysisReport
from query_analyzer.adapters.serializer import ReportSerializer
from query_analyzer.tui.report_renderer import ReportRenderer


@pytest.fixture
def sample_report() -> QueryAnalysisReport:
    plan = PlanNode(
        node_type="Seq Scan",
        cost=12.5,
        estimated_rows=100,
        actual_rows=95,
        actual_time_ms=4.2,
        children=[PlanNode(node_type="Filter", actual_rows=95)],
        properties={"table": "users"},
    )
    return QueryAnalysisReport(
        engine="postgresql",
        query="SELECT * FROM users",
        execution_time_ms=4.2,
        plan_tree=plan,
        plan_summary="Seq Scan on users",
        analyzed_at=datetime(2026, 6, 10, tzinfo=UTC),
        raw_plan={"Plan": {"Node Type": "Seq Scan"}},
        metrics={"planning_time_ms": 0.3, "rows": 95},
    )


def test_plan_node_is_recursive(sample_report: QueryAnalysisReport) -> None:
    assert sample_report.plan_tree is not None
    assert sample_report.plan_tree.children[0].node_type == "Filter"


def test_report_contains_only_observed_contract(sample_report: QueryAnalysisReport) -> None:
    dumped = sample_report.model_dump()
    assert dumped["plan_summary"] == "Seq Scan on users"
    assert "score" not in dumped
    assert "warnings" not in dumped
    assert "recommendations" not in dumped


def test_report_rejects_non_positive_execution_time() -> None:
    with pytest.raises(ValueError):
        QueryAnalysisReport(engine="sqlite", query="SELECT 1", execution_time_ms=0)


def test_ai_interpretation_is_optional_and_separate() -> None:
    report = QueryAnalysisReport(
        engine="sqlite",
        query="SELECT 1",
        execution_time_ms=0.1,
        ai_analysis=AIAnalysisResult(
            summary="The plan returns one constant row.",
            observations=["No table access is reported."],
            recommendations=[],
        ),
    )
    assert report.ai_analysis is not None
    assert report.metrics == {}


def test_json_roundtrip(sample_report: QueryAnalysisReport) -> None:
    restored = ReportSerializer.from_json(ReportSerializer.to_json(sample_report))
    assert restored == sample_report


def test_markdown_contains_engine_data_not_score(sample_report: QueryAnalysisReport) -> None:
    markdown = ReportSerializer.to_markdown(sample_report)
    assert "Seq Scan on users" in markdown
    assert "planning_time_ms" in markdown
    assert "Score" not in markdown
    assert "Warnings" not in markdown


def test_renderer_builds_complete_report(sample_report: QueryAnalysisReport) -> None:
    assert ReportRenderer.render_summary(sample_report) is not None
    assert ReportRenderer.render_plan_tree(sample_report.plan_tree) is not None
    assert ReportRenderer.render_full_report(sample_report) is not None
