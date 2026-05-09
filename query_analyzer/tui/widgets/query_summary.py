"""Widget for displaying query metadata and summary."""

from __future__ import annotations

import re
from typing import Any

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Label, Static


class QuerySummary(Container):
    """Panel displaying query metadata (type, tables, joins, conditions).

    Extracts and displays:
    - Query type (SELECT, INSERT, UPDATE, DELETE, etc.)
    - Tables involved
    - Join count and types
    - WHERE clauses detected
    - ORDER BY, GROUP BY info
    """

    DEFAULT_CSS = """
    QuerySummary {
        width: 1fr;
        height: auto;
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

    QuerySummary .summary-row {
        width: 1fr;
        height: auto;
        margin-bottom: 1;
    }

    QuerySummary .summary-label {
        width: 15;
        text-align: right;
        margin-right: 1;
        text-style: bold;
        color: $text-muted;
    }

    QuerySummary .summary-value {
        width: 1fr;
        color: $text;
    }

    QuerySummary .no-data {
        color: $text-muted;
        text-style: italic;
    }
    """

    def compose(self) -> ComposeResult:
        """Render initial layout."""
        with Vertical():
            yield Label("Query Summary", classes="query-title")
            yield Static(id="summary-content")

    def render_summary(self, query: str, engine: str) -> None:
        """Extract and render query metadata.

        Args:
            query: SQL query text
            engine: Database engine name
        """
        summary_content = self.query_one("#summary-content", Static)

        try:
            metadata = self._extract_metadata(query, engine)
            lines = self._format_metadata(metadata)
            summary_content.update("\n".join(lines))
        except Exception as e:
            summary_content.update(f"[yellow]Error parsing query: {e}[/yellow]")

    def set_loading_state(self) -> None:
        """Show loading state."""
        summary_content = self.query_one("#summary-content", Static)
        summary_content.update("[yellow]Analyzing query...[/yellow]")

    def set_error(self, message: str = "Error analyzing query") -> None:
        """Show error state.

        Args:
            message: Error message to display
        """
        summary_content = self.query_one("#summary-content", Static)
        summary_content.update(f"[red]✗ {message}[/red]")

    def clear(self) -> None:
        """Clear summary content."""
        summary_content = self.query_one("#summary-content", Static)
        summary_content.update("")

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
                table_name = next(
                    (g for g in match.groups() if g is not None and g), ""
                )
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
