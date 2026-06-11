"""Widget for displaying query metadata and summary."""

from __future__ import annotations

import re
from typing import Any

from rich.syntax import Syntax
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.markup import escape as markup_escape
from textual.widgets import Button, Label, Static

from query_analyzer.adapters.models import QueryAnalysisReport


class QuerySummary(Container):
    """Panel displaying query metadata and analysis summary."""

    DEFAULT_CSS = """
    QuerySummary {
        width: 1fr;
        height: 1fr;
        border: solid $accent;
        padding: 1;
        background: $panel;
        margin-bottom: 1;
    }

    QuerySummary:focus {
        border: solid $primary;
    }

    QuerySummary .query-title {
        text-style: bold;
        margin-bottom: 1;
        color: $primary;
    }

    QuerySummary .section-label {
        text-style: bold;
        color: $text-muted;
        margin-top: 1;
        margin-bottom: 0;
    }

    QuerySummary .summary-section {
        margin-bottom: 1;
        height: auto;
    }

    QuerySummary .summary-sql-box {
        border: solid $accent;
        background: $boost;
        padding: 1;
        height: auto;
        min-height: 3;
        max-height: 12;
        overflow-y: scroll;
        margin-bottom: 1;
    }

    QuerySummary #btn-copy-query {
        width: auto;
        min-width: 20;
        height: 3;
    }
    """

    def compose(self) -> ComposeResult:
        """Render initial layout."""
        with Vertical(id="summary-container"):
            yield Label("Resumen de Consulta", classes="query-title")
            yield Static(id="summary-context", classes="summary-section")
            yield Static(id="summary-plan", classes="summary-section")
            yield Label("Consulta SQL:", classes="section-label")
            yield Static(id="summary-sql", classes="summary-sql-box")
            yield Button("Copiar Consulta", id="btn-copy-query")

    def render_summary(
        self, query: str, report: QueryAnalysisReport, profile_name: str = ""
    ) -> None:
        """Extract and render query metadata and context.

        Args:
            query: SQL query text
            report: QueryAnalysisReport object
            profile_name: Name of the active database profile
        """
        self._current_query = query

        # 1. Update Context
        context_static = self.query_one("#summary-context", Static)
        date_str = report.analyzed_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        context_text = (
            f"[bold]Contexto de la Consulta:[/bold]\n"
            f"  • [b]Perfil:[/b] {profile_name or 'Default'}\n"
            f"  • [b]Motor:[/b] {report.engine.upper()}\n"
            f"  • [b]Fecha:[/b] {date_str}\n"
            f"  • [b]Duración Total:[/b] {report.execution_time_ms:.2f} ms"
        )
        context_static.update(context_text)

        # 2. Update Plan Summary
        plan_static = self.query_one("#summary-plan", Static)
        plan_summary = report.plan_summary or "No se dispone de un resumen del plan."
        plan_text = f"[bold]Resumen de Operación Principal:[/bold]\n  {markup_escape(plan_summary)}"
        plan_static.update(plan_text)

        # 3. Update SQL syntax highlighting
        sql_static = self.query_one("#summary-sql", Static)
        sql_syntax = Syntax(query, "sql", theme="monokai", line_numbers=True)
        sql_static.update(sql_syntax)

    def set_loading_state(self) -> None:
        """Show loading state."""
        self.query_one("#summary-context", Static).update("[yellow]Analizando consulta...[/yellow]")
        self.query_one("#summary-plan", Static).update("")
        self.query_one("#summary-sql", Static).update("")

    def set_error(self, message: str = "Error al analizar la consulta") -> None:
        """Show error state.

        Args:
            message: Error message to display
        """
        self.query_one("#summary-context", Static).update(f"[red]✗ {message}[/red]")
        self.query_one("#summary-plan", Static).update("")
        self.query_one("#summary-sql", Static).update("")

    def clear(self) -> None:
        """Clear summary content."""
        self._current_query = ""
        self.query_one("#summary-context", Static).update("")
        self.query_one("#summary-plan", Static).update("")
        self.query_one("#summary-sql", Static).update("")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "btn-copy-query":
            query = getattr(self, "_current_query", None)
            if query:
                try:
                    self.app.copy_to_clipboard(query)
                    self.app.notify("Consulta copiada al portapapeles")
                except Exception as e:
                    self.app.notify(f"No se pudo copiar al portapapeles: {e}", severity="error")

    @staticmethod
    def _extract_metadata(query: str, engine: str) -> dict[str, Any]:
        """Extract metadata from query.

        Args:
            query: SQL query text
            engine: Database engine name

        Returns:
            Dictionary with extracted metadata
        """
        query_normalized = query.strip()
        query_upper = query_normalized.upper()

        metadata: dict[str, Any] = {
            "engine": engine,
            "query_type": QuerySummary._extract_query_type(query_upper),
            "tables": QuerySummary._extract_tables(query_normalized),
            "joins": QuerySummary._extract_joins(query_upper),
            "has_where": "WHERE" in query_upper,
            "has_group_by": "GROUP BY" in query_upper,
            "has_order_by": "ORDER BY" in query_upper,
            "has_limit": "LIMIT" in query_upper or "FETCH" in query_upper,
            "subqueries": QuerySummary._count_subqueries(query_normalized),
        }

        return metadata

    @staticmethod
    def _extract_query_type(query_upper: str) -> str:
        """Extract query type (SELECT, INSERT, UPDATE, DELETE, etc.).

        Args:
            query_upper: Query in uppercase

        Returns:
            Query type string
        """
        for query_type in [
            "INSERT",
            "UPDATE",
            "DELETE",
            "SELECT",
            "WITH",
            "CREATE",
            "ALTER",
            "DROP",
        ]:
            if query_upper.startswith(query_type):
                return query_type
        return "UNKNOWN"

    @staticmethod
    def _extract_tables(query: str) -> list[str]:
        """Extract table names from query.

        Uses simple heuristics to find FROM and JOIN clauses.

        Args:
            query: SQL query text

        Returns:
            List of table names
        """
        tables = []
        query_upper = query.upper()

        # Pattern: FROM|JOIN tablename
        # Simple regex to find table references
        patterns = [
            r"FROM\s+(?:(?:\"([^\"]+)\"|([`']?)(\w+)\2)|(\w+))",
            r"JOIN\s+(?:(?:\"([^\"]+)\"|([`']?)(\w+)\2)|(\w+))",
            r"INTO\s+(?:(?:\"([^\"]+)\"|([`']?)(\w+)\2)|(\w+))",
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, query_upper, re.IGNORECASE)
            for match in matches:
                # Get first non-None group
                table_name = next((g for g in match.groups() if g is not None and g), "")
                if table_name and table_name not in ("SELECT", "WHERE", "ON"):
                    # Find the original case from query
                    original = query[match.start() : match.end()]
                    # Extract table name preserving case
                    table_match = re.search(
                        r"(?:FROM|JOIN|INTO)\s+(?:(?:\"([^\"]+)\"|(?:[`'])?(\w+)(?:[`'])?)|(\w+))",
                        original,
                        re.IGNORECASE,
                    )
                    if table_match:
                        for g in table_match.groups():
                            if g:
                                if g not in tables:
                                    tables.append(g)

        return tables[:10]  # Limit to 10 tables to avoid clutter

    @staticmethod
    def _extract_joins(query_upper: str) -> dict[str, int]:
        """Extract join types and counts.

        Args:
            query_upper: Query in uppercase

        Returns:
            Dictionary with join type counts
        """
        joins = {
            "INNER": len(re.findall(r"INNER\s+JOIN", query_upper)),
            "LEFT": len(re.findall(r"LEFT\s+(?:OUTER\s+)?JOIN", query_upper)),
            "RIGHT": len(re.findall(r"RIGHT\s+(?:OUTER\s+)?JOIN", query_upper)),
            "FULL": len(re.findall(r"FULL\s+(?:OUTER\s+)?JOIN", query_upper)),
            "CROSS": len(re.findall(r"CROSS\s+JOIN", query_upper)),
        }
        return {k: v for k, v in joins.items() if v > 0}

    @staticmethod
    def _count_subqueries(query: str) -> int:
        """Count approximate number of subqueries.

        Args:
            query: SQL query text

        Returns:
            Approximate subquery count
        """
        # Simple heuristic: count parenthesized SELECTs
        subqueries = len(re.findall(r"\(\s*SELECT", query, re.IGNORECASE)) - 1
        return max(0, subqueries)  # Subtract 1 for the main query's parens

    @staticmethod
    def _format_metadata(metadata: dict[str, Any]) -> list[str]:
        """Format metadata for display.

        Args:
            metadata: Extracted metadata dictionary

        Returns:
            List of formatted lines
        """
        lines = []

        # Query type
        query_type = metadata.get("query_type", "UNKNOWN")
        lines.append(f"Type:      [cyan]{query_type}[/cyan]")

        # Engine
        engine = metadata.get("engine", "-").upper()
        lines.append(f"Engine:    [cyan]{engine}[/cyan]")

        # Tables
        tables = metadata.get("tables", [])
        if tables:
            table_str = ", ".join(tables[:5])
            if len(tables) > 5:
                table_str += f", +{len(tables) - 5} more"
            lines.append(f"Tables:    [green]{table_str}[/green]")
        else:
            lines.append("Tables:    [dim]none[/dim]")

        # Joins
        joins = metadata.get("joins", {})
        if joins:
            join_str = ", ".join(f"{k}({v})" for k, v in joins.items())
            lines.append(f"Joins:     [yellow]{join_str}[/yellow]")

        # Clauses
        clauses = []
        if metadata.get("has_where"):
            clauses.append("WHERE")
        if metadata.get("has_group_by"):
            clauses.append("GROUP BY")
        if metadata.get("has_order_by"):
            clauses.append("ORDER BY")
        if metadata.get("has_limit"):
            clauses.append("LIMIT")

        if clauses:
            lines.append(f"Clauses:   [blue]{', '.join(clauses)}[/blue]")

        # Subqueries
        subqueries = metadata.get("subqueries", 0)
        if subqueries > 0:
            lines.append(f"Subqueries: [magenta]{subqueries}[/magenta]")

        return lines
