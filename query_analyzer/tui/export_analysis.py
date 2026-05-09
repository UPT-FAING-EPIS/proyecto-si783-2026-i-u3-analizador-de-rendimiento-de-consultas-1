"""Export functionality for query analysis reports."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from query_analyzer.adapters.models import QueryAnalysisReport


class ExportFormat:
    """Enum-like class for export formats."""

    JSON = "json"
    MARKDOWN = "markdown"
    SQL = "sql"

    @staticmethod
    def all() -> list[str]:
        """Get all available formats.

        Returns:
            List of format strings
        """
        return [ExportFormat.JSON, ExportFormat.MARKDOWN, ExportFormat.SQL]


class AnalysisExporter:
    """Exporter for query analysis reports.

    Supports exporting to JSON, Markdown, and SQL formats.
    """

    def __init__(self, report: QueryAnalysisReport) -> None:
        """Initialize exporter with a report.

        Args:
            report: QueryAnalysisReport to export
        """
        self.report = report

    def to_json(self, pretty: bool = True) -> str:
        """Export report as JSON.

        Args:
            pretty: Whether to format with indentation

        Returns:
            JSON string
        """
        data = self.report.model_dump(mode="json")
        if pretty:
            return json.dumps(data, indent=2, default=str)
        return json.dumps(data, default=str)

    def to_markdown(self) -> str:
        """Export report as Markdown.

        Returns:
            Markdown formatted string
        """
        lines = []

        # Header
        lines.append("# Query Analysis Report")
        lines.append("")
        lines.append(f"Generated: {self.report.analyzed_at.isoformat()}")
        lines.append(f"Engine: **{self.report.engine.upper()}**")
        lines.append("")

        # Query section
        lines.append("## Query")
        lines.append("")
        lines.append("```sql")
        lines.append(self.report.query)
        lines.append("```")
        lines.append("")

        # Execution metrics
        lines.append("## Execution Metrics")
        lines.append("")
        lines.append(f"- **Execution Time**: {self.report.execution_time_ms:.2f} ms")

        if self.report.plan_summary:
            lines.append(f"- **Plan**: {self.report.plan_summary}")
        lines.append("")

        # Plan tree
        if self.report.plan_tree:
            lines.append("## Execution Plan")
            lines.append("")
            lines.append("```")
            plan_text = self._format_plan_tree(self.report.plan_tree)
            lines.append(plan_text)
            lines.append("```")
            lines.append("")

        # AI Analysis
        if self.report.ai_analysis:
            ai = self.report.ai_analysis

            if ai.summary:
                lines.append("## AI Analysis Summary")
                lines.append("")
                lines.append(ai.summary)
                lines.append("")

            if ai.observations:
                lines.append("## Observations")
                lines.append("")
                for obs in ai.observations:
                    lines.append(f"- {obs}")
                lines.append("")

            if ai.recommendations:
                lines.append("## Recommendations")
                lines.append("")
                for i, rec in enumerate(ai.recommendations, 1):
                    lines.append(f"{i}. {rec}")
                lines.append("")

        return "\n".join(lines)

    def to_sql(self) -> str:
        """Export report as SQL with recommendations and comments.

        Returns:
            SQL formatted string with comments
        """
        lines = []

        # Header comment
        lines.append("-- Query Analysis Report")
        lines.append(f"-- Generated: {self.report.analyzed_at.isoformat()}")
        lines.append(f"-- Engine: {self.report.engine.upper()}")
        lines.append(f"-- Execution Time: {self.report.execution_time_ms:.2f}ms")
        lines.append("")

        # Plan summary
        if self.report.plan_summary:
            lines.append(f"-- Plan: {self.report.plan_summary}")
            lines.append("")

        # AI recommendations as comments
        if self.report.ai_analysis and self.report.ai_analysis.recommendations:
            lines.append("-- AI Recommendations:")
            for i, rec in enumerate(
                self.report.ai_analysis.recommendations, 1
            ):
                lines.append(f"-- {i}. {rec}")
            lines.append("")

        # Original query
        lines.append("-- Original Query:")
        lines.append(self.report.query + ";")

        return "\n".join(lines)

    def save_to_file(
        self,
        filepath: str | Path,
        format: str = ExportFormat.JSON,
    ) -> Path:
        """Save report to file.

        Args:
            filepath: Path to save file
            format: Export format (json, markdown, sql)

        Returns:
            Path object of saved file

        Raises:
            ValueError: If format is not supported
        """
        if format not in ExportFormat.all():
            raise ValueError(f"Unsupported format: {format}")

        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        if format == ExportFormat.JSON:
            content = self.to_json(pretty=True)
        elif format == ExportFormat.MARKDOWN:
            content = self.to_markdown()
        elif format == ExportFormat.SQL:
            content = self.to_sql()
        else:
            raise ValueError(f"Unsupported format: {format}")

        path.write_text(content, encoding="utf-8")
        return path

    @staticmethod
    def auto_filename(
        query_text: str,
        engine: str,
        format: str = ExportFormat.JSON,
        max_len: int = 30,
    ) -> str:
        """Generate automatic filename based on query and engine.

        Args:
            query_text: SQL query
            engine: Database engine
            format: Export format
            max_len: Maximum length of query part in filename

        Returns:
            Suggested filename
        """
        # Extract first few words from query and sanitize for filesystem safety
        words = query_text.strip().split()[:3]
        query_part = "_".join(words).replace(";", "").lower()
        query_part = AnalysisExporter._sanitize_filename_part(query_part)
        query_part = query_part[:max_len]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extension = f".{format}"

        if not query_part:
            query_part = "query"

        return f"{query_part}_{engine}_{timestamp}{extension}"

    @staticmethod
    def _sanitize_filename_part(value: str) -> str:
        """Sanitize a filename fragment for cross-platform compatibility."""
        sanitized = re.sub(r"[^a-z0-9_-]+", "_", value)
        sanitized = re.sub(r"_+", "_", sanitized)
        return sanitized.strip("_")

    @staticmethod
    def _format_plan_tree(
        node,
        depth: int = 0,
        is_last: bool = True,
        prefix: str = "",
    ) -> str:
        """Format plan tree for markdown display.

        Args:
            node: PlanNode to format
            depth: Current depth in tree
            is_last: Whether this is last child
            prefix: Prefix string for tree lines

        Returns:
            Formatted tree string
        """
        lines = []

        # Build tree connector
        if depth > 0:
            connector = "└─ " if is_last else "├─ "
            new_prefix = prefix + ("   " if is_last else "│  ")
        else:
            connector = ""
            new_prefix = ""

        # Node info
        node_info = f"{node.node_type}"
        if node.cost is not None:
            node_info += f" (cost: {node.cost:.2f})"
        if node.actual_rows is not None:
            node_info += f" [rows: {node.actual_rows}]"

        lines.append(f"{prefix}{connector}{node_info}")

        # Recursively format children
        for i, child in enumerate(node.children):
            is_last_child = i == len(node.children) - 1
            child_lines = AnalysisExporter._format_plan_tree(
                child,
                depth + 1,
                is_last_child,
                new_prefix,
            )
            lines.append(child_lines)

        return "\n".join(lines)
