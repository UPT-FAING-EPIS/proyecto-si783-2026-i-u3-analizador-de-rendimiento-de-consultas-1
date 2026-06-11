"""Tests for factual CLI report output."""

from unittest.mock import patch

from query_analyzer.adapters import QueryAnalysisReport
from query_analyzer.cli.utils import OutputFormatter


def _report() -> QueryAnalysisReport:
    return QueryAnalysisReport(
        engine="postgresql",
        query="SELECT id, name FROM users WHERE active = true",
        execution_time_ms=12.4,
        plan_summary="Index Scan on users",
        metrics={"actual_rows": 12, "estimated_rows": 10},
    )


def test_rich_output_shows_observed_data() -> None:
    with patch("query_analyzer.cli.utils.get_terminal_width", return_value=90):
        output = OutputFormatter.format_report(_report(), format="rich")
    assert "OBSERVED EXECUTION DATA" in output
    assert "Index Scan on users" in output
    assert "actual_rows" in output
    assert "Score" not in output


def test_markdown_output_uses_serializer() -> None:
    output = OutputFormatter.format_report(_report(), format="markdown")
    assert "# Query Analysis Report" in output
    assert "Index Scan on users" in output
