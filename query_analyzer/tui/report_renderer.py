"""Rich rendering for factual query analysis reports."""

from __future__ import annotations

from typing import Any

from rich.console import Group
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.tree import Tree

from query_analyzer.adapters.models import PlanNode, QueryAnalysisReport


class ReportRenderer:
    """Render engine observations separately from optional AI interpretation."""

    @staticmethod
    def render_summary(report: QueryAnalysisReport) -> Panel:
        """Render factual report metadata."""
        summary = report.plan_summary or "No summary reported by the adapter"
        content = (
            f"[bold]{report.engine.upper()}[/bold]\n"
            f"Execution: {report.execution_time_ms:.2f} ms\n"
            f"Plan: {summary}\n"
            f"Analyzed: {report.analyzed_at.isoformat()}"
        )
        return Panel(content, title="Observed execution data", expand=False)

    @staticmethod
    def render_plan_tree(plan: PlanNode | None) -> Tree:
        """Render the normalized execution plan."""
        if not plan:
            return Tree("[dim]No execution tree available[/dim]")

        root_tree = Tree(ReportRenderer._format_plan_node(plan))
        ReportRenderer._build_plan_tree_recursively(plan, root_tree)
        return root_tree

    @staticmethod
    def render_full_report(report: QueryAnalysisReport) -> Group:
        """Compose a complete report without subjective scoring."""
        components: list[Any] = [
            ReportRenderer.render_summary(report),
            "",
            Panel(
                Syntax(report.query, "sql", theme="monokai", line_numbers=True, word_wrap=True),
                title="Query",
                expand=False,
            ),
        ]

        if report.plan_tree:
            components.extend(
                [
                    "",
                    Panel(
                        ReportRenderer.render_plan_tree(report.plan_tree),
                        title="Execution plan",
                        expand=False,
                    ),
                ]
            )
        elif report.raw_plan:
            import json

            formatted_json = json.dumps(report.raw_plan, indent=2, ensure_ascii=False)
            components.extend(
                [
                    "",
                    Panel(
                        Syntax(
                            formatted_json,
                            "json",
                            theme="monokai",
                            line_numbers=True,
                            word_wrap=True,
                        ),
                        title="Raw Execution Plan",
                        expand=False,
                    ),
                ]
            )

        if report.metrics:
            components.extend(["", ReportRenderer._render_metrics_table(report.metrics)])

        if report.ai_analysis:
            ai = report.ai_analysis
            ai_lines = [ai.summary]
            if ai.observations:
                ai_lines.extend(["", "Observations:", *[f"- {item}" for item in ai.observations]])
            if ai.recommendations:
                ai_lines.extend(["", "Suggestions:", *[f"- {item}" for item in ai.recommendations]])
            components.extend(
                [
                    "",
                    Panel(
                        "\n".join(ai_lines),
                        title="AI interpretation (not engine data)",
                        expand=False,
                    ),
                ]
            )

        return Group(*components)

    @staticmethod
    def _format_plan_node(node: PlanNode) -> str:
        label = f"[bold]{node.node_type}[/bold]"
        details = []
        if node.cost is not None:
            details.append(f"cost={node.cost:.2f}")
        if node.estimated_rows is not None:
            details.append(f"estimated_rows={node.estimated_rows}")
        if node.actual_rows is not None:
            details.append(f"actual_rows={node.actual_rows}")
        if node.actual_time_ms is not None:
            details.append(f"time={node.actual_time_ms:.2f}ms")
        if details:
            label += f" [dim]({', '.join(details)})[/dim]"
        return label

    @staticmethod
    def _build_plan_tree_recursively(node: PlanNode, parent_tree: Tree) -> None:
        for child in node.children:
            child_tree = parent_tree.add(ReportRenderer._format_plan_node(child))
            ReportRenderer._build_plan_tree_recursively(child, child_tree)

    @staticmethod
    def _render_metrics_table(metrics: dict[str, Any]) -> Panel:
        table = Table(show_header=True, header_style="bold")
        table.add_column("Metric", style="cyan")
        table.add_column("Observed value")
        for key, value in metrics.items():
            table.add_row(str(key), str(value))
        return Panel(table, title="Engine metrics", expand=False)
