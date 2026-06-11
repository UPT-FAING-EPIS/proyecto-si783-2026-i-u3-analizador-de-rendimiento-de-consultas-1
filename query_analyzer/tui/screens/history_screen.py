"""History screen for browsing past query analyses."""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Input, Static, TabbedContent, TabPane

from query_analyzer.tui.history_manager import AnalysisRecord, get_history_manager
from query_analyzer.tui.widgets import (
    AIInsightsPanel,
    MetricsPanel,
    PlanTreeWidget,
    QuerySummary,
)


class HistoryScreen(Screen[AnalysisRecord | None]):
    """Screen for browsing and managing query analysis history.

    Layout:
    - Top: Search box and filters
    - Main area (horizontal split):
      - Left: History list
      - Right: Detailed view of selected analysis
    """

    BINDINGS = [
        Binding("1", "select_tab_summary", "Res", priority=True),
        Binding("2", "select_tab_metrics", "Met", priority=True),
        Binding("3", "select_tab_plan", "Plan", priority=True),
        Binding("4", "select_tab_ai", "IA", priority=True),
        Binding("ctrl+right", "next_tab", "Sig", priority=True),
        Binding("ctrl+left", "previous_tab", "Ant", priority=True),
        Binding("/", "focus_search", "Buscar", priority=True),
        Binding("l", "focus_list", "Lista", priority=True),
        Binding("b", "focus_buttons", "Botones", priority=True),
        Binding("t", "focus_tabs", "Pestañas", priority=True),
        ("escape", "go_back", "Volver"),
        ("j", "select_next", "Siguiente"),
        ("k", "select_previous", "Anterior"),
        ("g", "select_first", "Inicio"),
        ("shift+g", "select_last", "Fin"),
        ("down", "select_next", "Siguiente"),
        ("up", "select_previous", "Anterior"),
        ("delete", "delete_selected", "Borrar"),
        ("y", "copy_query", "Copiar Query"),
        ("c", "clear_history", "Limpiar"),
        ("enter", "load_selected", "Cargar"),
        ("q", "quit", "Salir"),
    ]

    DEFAULT_CSS = """
    HistoryScreen {
        background: $background;
    }

    HistoryScreen #history-root {
        layout: vertical;
        height: 1fr;
        width: 1fr;
        padding: 0 1;
    }

    HistoryScreen #header {
        height: auto;
        margin-bottom: 1;
    }

    HistoryScreen .header-title {
        width: 100%;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    HistoryScreen #search-box {
        width: 1fr;
        height: auto;
        margin-bottom: 1;
    }

    HistoryScreen #workspace {
        layout: horizontal;
        height: 1fr;
        min-height: 15;
    }

    HistoryScreen #list-column {
        width: 3fr;
        height: 1fr;
        margin-right: 1;
        border: solid $accent;
        padding: 1;
    }

    HistoryScreen #history-list {
        width: 1fr;
        height: 1fr;
        background: $panel;
        border: solid $surface-lighten-1;
        overflow-y: auto;
        scrollbar-size-vertical: 0;
    }

    HistoryScreen #history-list:focus {
        scrollbar-size-vertical: 1;
    }

    HistoryScreen .history-item {
        width: 1fr;
        height: auto;
        padding: 1;
        margin-bottom: 1;
        border: solid $surface-lighten-2;
    }

    HistoryScreen .history-item:hover {
        background: $surface-lighten-2;
    }

    HistoryScreen .history-item.selected {
        background: $primary;
        color: $background;
    }

    HistoryScreen .history-item-time {
        color: $text-muted;
        width: 15;
    }

    HistoryScreen .history-item-query {
        width: 1fr;
    }

    HistoryScreen .history-item-profile {
        color: $text-muted;
        width: 15;
    }

    HistoryScreen #detail-column {
        width: 2fr;
        height: 1fr;
    }

    HistoryScreen #detail-tabbed {
        width: 1fr;
        height: 1fr;
        border: solid $accent;
    }

    HistoryScreen TabPane {
        padding: 1;
        overflow-y: auto;
        scrollbar-size-vertical: 0;
    }

    HistoryScreen TabPane:focus {
        scrollbar-size-vertical: 1;
    }

    HistoryScreen #detail-column QuerySummary {
        height: auto;
        max-height: 9;
    }

    HistoryScreen #detail-column Static {
        height: auto;
    }

    HistoryScreen #actions-row {
        height: auto;
        margin-top: 1;
        margin-bottom: 1;
    }

    HistoryScreen #btn-load {
        width: 12;
        margin-right: 1;
    }

    HistoryScreen #btn-delete {
        width: 10;
        margin-right: 1;
    }

    HistoryScreen #btn-copy-query {
        width: 14;
        margin-right: 1;
    }

    HistoryScreen #btn-clear {
        width: 10;
    }

    HistoryScreen #status-bar {
        height: auto;
        margin-top: 1;
        color: $text-muted;
    }
    """

    def __init__(self, profile_name: str) -> None:
        super().__init__()
        self._profile_name = profile_name
        self._history = get_history_manager()
        self._filtered_records = self._history.get_all_for_profile(profile_name)
        self._selected_index = 0

    def compose(self) -> ComposeResult:
        """Compose screen layout."""
        with Vertical(id="history-root"):
            # Header
            with Container(id="header"):
                yield Static("Analysis History", classes="header-title")
                yield Input(
                    placeholder="Buscar query o perfil...",
                    id="search-box",
                )

            # Main workspace
            with Horizontal(id="workspace"):
                # Left: History list
                with Vertical(id="list-column"):
                    yield DataTable(id="history-list")

                # Right: Details
                with Vertical(id="detail-column"):
                    with TabbedContent(initial="tab-summary", id="detail-tabbed"):
                        with TabPane("Resumen", id="tab-summary"):
                            yield QuerySummary()
                        with TabPane("Métricas", id="tab-metrics"):
                            yield MetricsPanel()
                        with TabPane("Plan", id="tab-plan"):
                            yield PlanTreeWidget()
                        with TabPane("IA", id="tab-ai"):
                            yield AIInsightsPanel()

            # Actions
            with Horizontal(id="actions-row"):
                yield Button("Cargar", variant="primary", id="btn-load")
                yield Button("Borrar", id="btn-delete")
                yield Button("Copiar Query", id="btn-copy-query")
                yield Button("Limpiar Histórico", id="btn-clear")

            # Status bar
            yield Static(id="status-bar")

        yield Footer()

    def on_mount(self) -> None:
        """Mount screen and render initial content."""
        table = self.query_one("#history-list", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.add_column("Hora", width=10)
        table.add_column("Query", width=44)
        table.add_column("Perfil", width=18)
        self._render_list()
        self._render_detail()
        self._update_status()
        self.query_one("#search-box", Input).focus()

    def action_focus_search(self) -> None:
        """Focus search input."""
        self.query_one("#search-box", Input).focus()

    def action_focus_list(self) -> None:
        """Focus history list table."""
        self.query_one("#history-list", DataTable).focus()

    def action_focus_buttons(self) -> None:
        """Focus first action button."""
        self.query_one("#btn-load", Button).focus()

    def action_focus_tabs(self) -> None:
        """Focus tabbed detail panel."""
        self.query_one("#detail-tabbed", TabbedContent).focus()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Sync selected index when highlighted row changes."""
        if event.data_table.id != "history-list":
            return
        if event.cursor_row < 0 or event.cursor_row >= len(self._filtered_records):
            return
        self._selected_index = event.cursor_row
        self._render_detail()
        self._update_status()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Load selected history row when pressing Enter in table."""
        if event.data_table.id != "history-list":
            return

        if event.cursor_row < 0 or event.cursor_row >= len(self._filtered_records):
            return

        self._selected_index = event.cursor_row
        self.action_load_selected()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes.

        Args:
            event: Input changed event
        """
        search_text = event.value.strip()

        if not search_text:
            self._filtered_records = self._history.get_all_for_profile(self._profile_name)
        else:
            # Search in both query text and profile names
            search_lower = search_text.lower()
            self._filtered_records = [
                r
                for r in self._history.get_all_for_profile(self._profile_name)
                if search_lower in r.query.lower() or search_lower in r.profile_name.lower()
            ]

        self._selected_index = 0
        self._render_list()
        self._render_detail()
        self._update_status()

    def action_go_back(self) -> None:
        """Go back to previous screen."""
        if self.query_one("#search-box", Input).has_focus:
            self.action_focus_list()
            return
        self.dismiss(None)

    def action_select_next(self) -> None:
        """Select next item in list."""
        if self._filtered_records:
            self._selected_index = (self._selected_index + 1) % len(self._filtered_records)
            self._render_list()
            self._render_detail()

    def action_select_previous(self) -> None:
        """Select previous item in list."""
        if self._filtered_records:
            self._selected_index = (self._selected_index - 1) % len(self._filtered_records)
            self._render_list()
            self._render_detail()

    def action_select_first(self) -> None:
        """Select first item in list."""
        if self._filtered_records:
            self._selected_index = 0
            self._render_list()
            self._render_detail()

    def action_select_last(self) -> None:
        """Select last item in list."""
        if self._filtered_records:
            self._selected_index = len(self._filtered_records) - 1
            self._render_list()
            self._render_detail()

    def action_load_selected(self) -> None:
        """Load selected analysis (returns to analysis screen)."""
        if not self._filtered_records:
            return

        record = self._filtered_records[self._selected_index]
        self.dismiss(record)

    def action_delete_selected(self) -> None:
        """Delete selected record from history."""
        if not self._filtered_records:
            return

        record = self._filtered_records[self._selected_index]
        self._history.delete_record(record)

        # Re-filter and render
        search_box = self.query_one("#search-box", Input)
        search_text = search_box.value
        if search_text:
            search_lower = search_text.lower()
            self._filtered_records = [
                r
                for r in self._history.get_all_for_profile(self._profile_name)
                if search_lower in r.query.lower() or search_lower in r.profile_name.lower()
            ]
        else:
            self._filtered_records = self._history.get_all_for_profile(self._profile_name)

        if self._filtered_records and self._selected_index >= len(self._filtered_records):
            self._selected_index = len(self._filtered_records) - 1

        self._render_list()
        self._render_detail()
        self._update_status()

    def action_clear_history(self) -> None:
        """Clear all history after confirmation."""
        self._history.clear_profile(self._profile_name)
        self._filtered_records = []
        self._selected_index = 0
        self._render_list()
        self._clear_detail()
        self._update_status()

    def action_quit(self) -> None:
        """Exit the application."""
        self.app.exit()

    def action_copy_query(self) -> None:
        """Copy selected query (simulated feedback)."""
        self.on_copy_query_pressed()

    def action_select_tab_summary(self) -> None:
        """Switch to Summary tab."""
        try:
            self.query_one("#detail-tabbed", TabbedContent).active = "tab-summary"
        except Exception:
            pass

    def action_select_tab_metrics(self) -> None:
        """Switch to Metrics tab."""
        try:
            self.query_one("#detail-tabbed", TabbedContent).active = "tab-metrics"
        except Exception:
            pass

    def action_select_tab_plan(self) -> None:
        """Switch to Plan tab."""
        try:
            self.query_one("#detail-tabbed", TabbedContent).active = "tab-plan"
        except Exception:
            pass

    def action_select_tab_ai(self) -> None:
        """Switch to AI tab."""
        try:
            self.query_one("#detail-tabbed", TabbedContent).active = "tab-ai"
        except Exception:
            pass

    def action_next_tab(self) -> None:
        """Move to next tab."""
        try:
            tabbed = self.query_one("#detail-tabbed", TabbedContent)
            tab_ids = ["tab-summary", "tab-metrics", "tab-plan", "tab-ai"]
            idx = tab_ids.index(tabbed.active)
            tabbed.active = tab_ids[(idx + 1) % len(tab_ids)]
        except Exception:
            pass

    def action_previous_tab(self) -> None:
        """Move to previous tab."""
        try:
            tabbed = self.query_one("#detail-tabbed", TabbedContent)
            tab_ids = ["tab-summary", "tab-metrics", "tab-plan", "tab-ai"]
            idx = tab_ids.index(tabbed.active)
            tabbed.active = tab_ids[(idx - 1) % len(tab_ids)]
        except Exception:
            pass

    @on(Button.Pressed, "#btn-load")
    def on_load_pressed(self) -> None:
        """Load button pressed."""
        self.action_load_selected()

    @on(Button.Pressed, "#btn-delete")
    def on_delete_pressed(self) -> None:
        """Delete button pressed."""
        self.action_delete_selected()

    @on(Button.Pressed, "#btn-copy-query")
    def on_copy_query_pressed(self) -> None:
        """Copy query button pressed."""
        if not self._filtered_records:
            return

        # In a real app, this would copy to clipboard
        # For now, just show a message
        status = self.query_one("#status-bar", Static)
        status.update("[green]✓ Query copied to clipboard (simulated)[/green]")

    @on(Button.Pressed, "#btn-clear")
    def on_clear_pressed(self) -> None:
        """Clear history button pressed."""
        self.action_clear_history()

    def _render_list(self) -> None:
        """Render history list."""
        list_widget = self.query_one("#history-list", DataTable)
        list_widget.clear(columns=False)

        if not self._filtered_records:
            return

        for record in self._filtered_records:
            time_str = record.created_at.strftime("%H:%M:%S")
            query_preview = record.query_preview(40)
            profile_str = record.profile_name
            list_widget.add_row(time_str, query_preview, profile_str, key=record.id)

        if self._selected_index >= len(self._filtered_records):
            self._selected_index = len(self._filtered_records) - 1

        list_widget.move_cursor(row=self._selected_index, column=0)

    def _render_detail(self) -> None:
        """Render detail view for selected record."""
        if not self._filtered_records:
            self._clear_detail()
            return

        record = self._filtered_records[self._selected_index]

        # Update query summary
        summary_widget = self.query_one(QuerySummary)
        summary_widget.render_summary(record.query, record.report, record.profile_name)

        # Update metrics
        metrics_widget = self.query_one(MetricsPanel)
        metrics_widget.render_metrics(
            record.report.execution_time_ms,
            record.report.plan_tree,
            record.report.metrics,
        )

        # Update plan tree
        plan_widget = self.query_one(PlanTreeWidget)
        plan_widget.render_plan(record.report.plan_tree)

        # Update AI insights
        ai_widget = self.query_one(AIInsightsPanel)
        ai_widget.render_ai_analysis(record.report.ai_analysis)

    def _clear_detail(self) -> None:
        """Clear all detail panels."""
        self.query_one(QuerySummary).clear()
        self.query_one(MetricsPanel).clear()
        self.query_one(PlanTreeWidget).clear()
        self.query_one(AIInsightsPanel).clear()

    def _update_status(self) -> None:
        """Update status bar."""
        status = self.query_one("#status-bar", Static)

        if not self._filtered_records:
            status.update("[yellow]No hay análisis en el histórico[/yellow]")
            return

        total = len(self._history.get_all_for_profile(self._profile_name))
        current = self._selected_index + 1
        filtered = len(self._filtered_records)

        if filtered == total:
            status.update(f"[dim]{current}/{total} análisis[/dim]")
        else:
            status.update(f"[dim]{current}/{filtered} (mostrando) de {total} total[/dim]")
