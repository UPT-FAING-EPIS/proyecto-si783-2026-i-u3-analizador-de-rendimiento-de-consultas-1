"""Widget for displaying query execution metrics."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.markup import escape as markup_escape
from textual.widgets import Label, Static

from query_analyzer.adapters.models import PlanNode


class MetricsPanel(Container):
    """Panel displaying execution metrics from the query plan.

    Metrics displayed:
    - Execution Time (ms)
    - Rows Examined
    - Rows Returned
    - Plan Nodes
    - Join Operations
    - Sort Operations
    - Index Usage
    - Execution Ratio
    """

    DEFAULT_CSS = """
    MetricsPanel {
        width: 1fr;
        height: auto;
        border: solid $accent;
        padding: 1;
        background: $panel;
        margin-bottom: 1;
    }

    MetricsPanel:focus {
        border: solid $primary;
    }

    MetricsPanel .metrics-title {
        text-style: bold;
        margin-bottom: 1;
        color: $primary;
    }

    MetricsPanel .metric-row {
        width: 1fr;
        height: auto;
        margin-bottom: 1;
    }

    MetricsPanel .metric-label {
        width: 15;
        text-align: right;
        margin-right: 1;
        text-style: bold;
        color: $text-muted;
    }

    MetricsPanel .metric-value {
        width: 1fr;
        color: $text;
    }

    MetricsPanel .no-data {
        color: $text-muted;
        text-style: italic;
    }
    """

    def compose(self) -> ComposeResult:
        """Render initial layout."""
        with Vertical():
            yield Label("Execution Metrics", classes="metrics-title")
            yield Static(id="metrics-content")

    def render_metrics(
        self,
        execution_time_ms: float,
        plan_tree: PlanNode | None,
        observed_metrics: dict[str, Any] | None = None,
    ) -> None:
        """Extract and render execution metrics from plan.

        Args:
            execution_time_ms: Total execution time in milliseconds
            plan_tree: Root node of execution plan tree
            observed_metrics: Metrics returned directly by the adapter
        """
        metrics_content = self.query_one("#metrics-content", Static)

        try:
            metrics = self._extract_metrics(execution_time_ms, plan_tree)
            if observed_metrics:
                metrics["engine_metrics"] = observed_metrics
            lines = self._format_metrics(metrics)
            metrics_content.update("\n".join(lines))
        except Exception as e:
            metrics_content.update(
                f"[yellow]Error analyzing metrics: {markup_escape(str(e))}[/yellow]"
            )

    def set_loading_state(self) -> None:
        """Show loading state."""
        metrics_content = self.query_one("#metrics-content", Static)
        metrics_content.update("[yellow]Calculating metrics...[/yellow]")

    def set_error(self, message: str = "Error analyzing metrics") -> None:
        """Show error state.

        Args:
            message: Error message to display
        """
        metrics_content = self.query_one("#metrics-content", Static)
        metrics_content.update(f"[red]✗ {message}[/red]")

    def clear(self) -> None:
        """Clear metrics content."""
        metrics_content = self.query_one("#metrics-content", Static)
        metrics_content.update("")

    @staticmethod
    def _extract_metrics(
        execution_time_ms: float,
        plan_tree: PlanNode | None,
    ) -> dict[str, Any]:
        """Extract metrics from plan tree.

        Args:
            execution_time_ms: Total execution time in milliseconds
            plan_tree: Root node of execution plan tree

        Returns:
            Dictionary with extracted metrics
        """
        metrics: dict[str, Any] = {
            "execution_time_ms": execution_time_ms,
            "total_rows_examined": 0,
            "total_rows_returned": 0,
            "total_cost": 0.0,
            "node_count": 0,
            "join_count": 0,
            "sort_count": 0,
            "index_count": 0,
            "max_depth": 0,
            "rows_divergence": None,
        }

        if plan_tree:
            metrics.update(MetricsPanel._traverse_plan_tree(plan_tree, metrics, depth=0))

        return metrics

    @staticmethod
    def _traverse_plan_tree(
        node: PlanNode,
        metrics: dict[str, Any],
        depth: int,
    ) -> dict[str, Any]:
        """Traverse plan tree and accumulate metrics.

        Args:
            node: Current plan node
            metrics: Metrics accumulator dictionary
            depth: Current depth in tree

        Returns:
            Updated metrics dictionary
        """
        # Update row counts
        if node.actual_rows is not None:
            metrics["total_rows_returned"] = max(
                metrics["total_rows_returned"],
                node.actual_rows,
            )

        # Try to estimate rows examined (first node usually)
        if node.estimated_rows is not None:
            metrics["total_rows_examined"] = max(
                metrics["total_rows_examined"],
                node.estimated_rows,
            )

        # Update cost
        if node.cost is not None:
            metrics["total_cost"] += node.cost

        # Count nodes
        metrics["node_count"] += 1

        # Update max depth
        metrics["max_depth"] = max(metrics["max_depth"], depth)

        # Count specific node types
        node_type_lower = node.node_type.lower()
        if "join" in node_type_lower:
            metrics["join_count"] += 1
        if "sort" in node_type_lower:
            metrics["sort_count"] += 1
        if "index" in node_type_lower or "idx" in node_type_lower:
            metrics["index_count"] += 1

        # Calculate rows divergence (actual vs estimated)
        if (
            node.actual_rows is not None
            and node.estimated_rows is not None
            and node.estimated_rows > 0
        ):
            divergence = abs((node.actual_rows - node.estimated_rows) / node.estimated_rows)
            if metrics["rows_divergence"] is None:
                metrics["rows_divergence"] = divergence
            else:
                metrics["rows_divergence"] = max(metrics["rows_divergence"], divergence)

        # Traverse children
        for child in node.children:
            MetricsPanel._traverse_plan_tree(child, metrics, depth + 1)

        return metrics

    @staticmethod
    def _flatten_metrics(val: Any, prefix: str = "") -> dict[str, Any]:
        """Flattens nested dicts/lists into a flat dictionary with dot notation.

        Args:
            val: The value to flatten (usually dict or list).
            prefix: The current prefix for keys.

        Returns:
            Flat dictionary of key-value pairs.
        """
        flat: dict[str, Any] = {}
        if isinstance(val, dict):
            for k, v in val.items():
                key = f"{prefix}.{k}" if prefix else k
                flat.update(MetricsPanel._flatten_metrics(v, key))
        elif isinstance(val, list):
            for idx, item in enumerate(val):
                key = f"{prefix}[{idx}]"
                flat.update(MetricsPanel._flatten_metrics(item, key))
        else:
            flat[prefix] = val
        return flat

    @staticmethod
    def _format_metric_value(val: Any) -> str:
        """Formats a metric value to be clearly differentiable for 0, False, None, and empty strings.

        Args:
            val: The metric value.

        Returns:
            A string representation of the formatted value.
        """
        if val is None:
            return "No disponible"
        if val is False:
            return "False"
        if val is True:
            return "True"
        if val == "":
            return '"" (cadena vacía)'
        return str(val)

    @staticmethod
    def _format_metrics(metrics: dict[str, Any]) -> list[str]:
        """Format metrics for display.

        Args:
            metrics: Extracted metrics dictionary

        Returns:
            List of formatted lines
        """
        lines = []

        # Execution time is factual; no subjective thresholds or colors.
        exec_time = metrics.get("execution_time_ms", 0)
        lines.append(f"Exec Time: [cyan]{exec_time:.2f} ms[/cyan]")

        # Rows examined
        rows_examined = metrics.get("total_rows_examined", 0)
        if rows_examined == 0:
            lines.append("Rows Examined: [dim]0[/dim]")
        else:
            lines.append(f"Rows Examined: [cyan]{rows_examined:,}[/cyan]")

        # Rows returned
        rows_returned = metrics.get("total_rows_returned", 0)
        if rows_returned == 0:
            lines.append("Rows Returned: [dim]0[/dim]")
        else:
            lines.append(f"Rows Returned: [cyan]{rows_returned:,}[/cyan]")

        # Plan nodes
        node_count = metrics.get("node_count", 0)
        if node_count > 0:
            lines.append(f"Nodes:    [cyan]{node_count}[/cyan]")

        # Joins
        join_count = metrics.get("join_count", 0)
        if join_count > 0:
            lines.append(f"Joins:    [cyan]{join_count}[/cyan]")

        # Sorts
        sort_count = metrics.get("sort_count", 0)
        if sort_count > 0:
            lines.append(f"Sorts:    [cyan]{sort_count}[/cyan]")

        # Indexes
        index_count = metrics.get("index_count", 0)
        if index_count > 0:
            lines.append(f"Indexes:  [cyan]{index_count}[/cyan]")

        # Rows divergence is a mathematical comparison, not a quality rating.
        divergence = metrics.get("rows_divergence")
        if divergence is not None:
            lines.append(f"Divergence: [cyan]{divergence * 100:.1f}%[/cyan]")

        # Tree depth
        max_depth = metrics.get("max_depth", 0)
        if max_depth > 0:
            lines.append(f"Depth:    [cyan]{max_depth}[/cyan]")

        observed = metrics.get("engine_metrics", {})
        if observed:
            lines.append("")
            lines.append("[bold]Engine metrics[/bold]")
            # Flatten the nested dictionary or list
            flat_observed = MetricsPanel._flatten_metrics(observed)
            # Sort keys alphabetically
            for key in sorted(flat_observed.keys()):
                val = flat_observed[key]
                formatted_val = MetricsPanel._format_metric_value(val)
                lines.append(
                    f"{markup_escape(str(key))}: [cyan]{markup_escape(formatted_val)}[/cyan]"
                )

        if not lines:
            lines.append("[dim]No metrics available[/dim]")

        return lines
