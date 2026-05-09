"""Widget for displaying execution plan tree visualization."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Label, Static

from query_analyzer.adapters.models import PlanNode


class PlanTreeWidget(Container):
    """Panel displaying hierarchical execution plan visualization.

    Features:
    - Tree structure visualization with indentation
    - Node type highlighting
    - Cost and row information
    - Collapsible/expandable nodes (future feature)
    """

    DEFAULT_CSS = """
    PlanTreeWidget {
        width: 1fr;
        height: auto;
        border: solid $accent;
        padding: 1;
        background: $panel;
        margin-bottom: 1;
        overflow-y: auto;
        scrollbar-size-vertical: 0;
    }

    PlanTreeWidget:focus {
        border: solid $primary;
        scrollbar-size-vertical: 1;
    }

    PlanTreeWidget .plan-title {
        text-style: bold;
        margin-bottom: 1;
        color: $primary;
    }

    PlanTreeWidget .tree-node {
        width: 1fr;
        height: auto;
        margin-bottom: 0;
    }

    PlanTreeWidget .node-content {
        width: 1fr;
    }

    PlanTreeWidget .node-type {
        text-style: bold;
    }

    PlanTreeWidget .node-info {
        color: $text-muted;
        margin-left: 1;
    }

    PlanTreeWidget .no-data {
        color: $text-muted;
        text-style: italic;
    }
    """

    def compose(self) -> ComposeResult:
        """Render initial layout."""
        with Vertical():
            yield Label("Execution Plan", classes="plan-title")
            yield Static(id="plan-content")

    def render_plan(self, plan_tree: PlanNode | None) -> None:
        """Render execution plan tree.

        Args:
            plan_tree: Root node of execution plan tree
        """
        plan_content = self.query_one("#plan-content", Static)

        try:
            if plan_tree is None:
                plan_content.update("[dim]No plan tree available[/dim]")
                return

            lines = self._format_plan_tree(plan_tree)
            plan_content.update("\n".join(lines))
        except Exception as e:
            plan_content.update(f"[yellow]Error rendering plan: {e}[/yellow]")

    def set_loading_state(self) -> None:
        """Show loading state."""
        plan_content = self.query_one("#plan-content", Static)
        plan_content.update("[yellow]Parsing execution plan...[/yellow]")

    def set_error(self, message: str = "Error rendering plan") -> None:
        """Show error state.

        Args:
            message: Error message to display
        """
        plan_content = self.query_one("#plan-content", Static)
        plan_content.update(f"[red]✗ {message}[/red]")

    def clear(self) -> None:
        """Clear plan content."""
        plan_content = self.query_one("#plan-content", Static)
        plan_content.update("")

    @staticmethod
    def _format_plan_tree(
        node: PlanNode,
        depth: int = 0,
        is_last: bool = True,
        prefix: str = "",
    ) -> list[str]:
        """Recursively format plan tree for display.

        Args:
            node: Current plan node
            depth: Current depth in tree
            is_last: Whether this is the last child
            prefix: Prefix string for tree lines

        Returns:
            List of formatted lines
        """
        lines = []

        # Build tree connector
        if depth > 0:
            connector = "└─ " if is_last else "├─ "
            new_prefix = prefix + ("   " if is_last else "│  ")
        else:
            connector = ""
            new_prefix = ""

        # Format node line
        node_line = PlanTreeWidget._format_node_line(node)
        lines.append(f"{prefix}{connector}{node_line}")

        # Recursively format children
        for i, child in enumerate(node.children):
            is_last_child = i == len(node.children) - 1
            child_lines = PlanTreeWidget._format_plan_tree(
                child,
                depth + 1,
                is_last_child,
                new_prefix,
            )
            lines.extend(child_lines)

        return lines

    @staticmethod
    def _format_node_line(node: PlanNode) -> str:
        """Format a single plan node for display.

        Args:
            node: Plan node to format

        Returns:
            Formatted node line
        """
        parts = []

        # Node type
        node_type_colored = PlanTreeWidget._colorize_node_type(node.node_type)
        parts.append(node_type_colored)

        # Cost
        if node.cost is not None:
            parts.append(f"[dim](cost: {node.cost:.2f})[/dim]")

        # Row information
        row_parts = []
        if node.estimated_rows is not None:
            row_parts.append(f"est={node.estimated_rows:,}")
        if node.actual_rows is not None:
            row_parts.append(f"actual={node.actual_rows:,}")

        if row_parts:
            row_info = ", ".join(row_parts)
            parts.append(f"[blue]({row_info})[/blue]")

        # Execution time
        if node.actual_time_ms is not None:
            if node.actual_time_ms < 1:
                color = "$success"
            elif node.actual_time_ms < 10:
                color = "$warning"
            else:
                color = "$error"
            parts.append(f"[{color}]{node.actual_time_ms:.2f}ms[/{color}]")

        # Additional properties
        if node.properties:
            prop_str = PlanTreeWidget._format_properties(node.properties)
            if prop_str:
                parts.append(f"[magenta]{prop_str}[/magenta]")

        return " ".join(parts)

    @staticmethod
    def _colorize_node_type(node_type: str) -> str:
        """Apply color based on node type.

        Args:
            node_type: Type of plan node

        Returns:
            Colored node type string
        """
        node_lower = node_type.lower()

        if "scan" in node_lower:
            if "index" in node_lower or "idx" in node_lower:
                return f"[green bold]{node_type}[/green bold]"
            elif "seq" in node_lower or "sequential" in node_lower:
                return f"[yellow bold]{node_type}[/yellow bold]"
            else:
                return f"[cyan bold]{node_type}[/cyan bold]"

        if "join" in node_lower:
            if "nested" in node_lower:
                return f"[yellow bold]{node_type}[/yellow bold]"
            else:
                return f"[blue bold]{node_type}[/blue bold]"

        if "sort" in node_lower:
            return f"[magenta bold]{node_type}[/magenta bold]"

        if "aggregate" in node_lower or "group" in node_lower:
            return f"[cyan bold]{node_type}[/cyan bold]"

        if "filter" in node_lower or "where" in node_lower:
            return f"[blue bold]{node_type}[/blue bold]"

        if "limit" in node_lower:
            return f"[green bold]{node_type}[/green bold]"

        if "hash" in node_lower:
            return f"[yellow bold]{node_type}[/yellow bold]"

        # Default styling
        return f"[white bold]{node_type}[/white bold]"

    @staticmethod
    def _format_properties(properties: dict[str, Any], max_items: int = 3) -> str:
        """Format node properties for display.

        Args:
            properties: Node properties dictionary
            max_items: Maximum properties to show

        Returns:
            Formatted properties string
        """
        if not properties:
            return ""

        # Select most relevant properties
        important_keys = [
            "table_name",
            "index_name",
            "filter_condition",
            "join_condition",
            "group_key",
            "sort_key",
            "output_fields",
        ]

        relevant_props = []
        for key in important_keys:
            if key in properties and properties[key]:
                relevant_props.append(f"{key}={properties[key]}")

        # Add remaining properties up to max_items
        for key, value in properties.items():
            if key not in important_keys and len(relevant_props) < max_items:
                if value:  # Only if not empty
                    relevant_props.append(f"{key}={value}")

        return ", ".join(relevant_props[:max_items])
