"""Widget for rendering AI analysis insights in TUI."""

from __future__ import annotations

from rich.syntax import Syntax
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.markup import escape as markup_escape
from textual.widgets import Label, ListItem, ListView, Static

from query_analyzer.adapters.models import AIAnalysisResult

# Severity text prefixes for observations (no emojis)
OBSERVATION_ICONS = {
    "CRITICAL": "[red bold][CRITICO][/red bold]",
    "HIGH": "[red bold][ALTO][/red bold]",
    "MEDIUM": "[yellow bold][MEDIO][/yellow bold]",
    "LOW": "[blue bold][INFO][/blue bold]",
}


class AIInsightsPanel(Container):
    """Panel for displaying AI-powered analysis insights.

    Displays:
    - AI Warning banner (permanent, no emojis)
    - AI Summary (natural language overview)
    - Observations (severity-based insights)
    - Recommendations (with SQL code snippets)
    - Placeholder if AI is not configured
    """

    DEFAULT_CSS = """
    AIInsightsPanel {
        width: 1fr;
        height: auto;
        border: solid $accent;
        padding: 1;
        background: $panel;
        overflow-y: auto;
        scrollbar-size-vertical: 0;
        margin-bottom: 1;
    }

    AIInsightsPanel:focus {
        border: solid $primary;
        scrollbar-size-vertical: 1;
    }

    AIInsightsPanel .panel-title {
        text-style: bold;
        margin-bottom: 1;
        color: $primary;
    }

    AIInsightsPanel .ai-warning-banner {
        background: $boost;
        border-left: solid $warning;
        padding: 0 1;
        margin-bottom: 1;
        color: $text-muted;
        text-style: italic;
    }

    AIInsightsPanel .section-title {
        text-style: bold;
        margin-top: 1;
        margin-bottom: 1;
        color: $accent;
    }

    AIInsightsPanel .summary-text {
        width: 1fr;
        margin-bottom: 1;
        color: $text;
    }

    AIInsightsPanel ListView {
        height: auto;
        border: solid $surface-lighten-1;
        overflow-y: auto;
        scrollbar-size-vertical: 0;
        margin-bottom: 1;
    }

    AIInsightsPanel ListView:focus {
        scrollbar-size-vertical: 1;
    }

    AIInsightsPanel ListItem {
        height: auto;
        padding: 0 1;
        margin-bottom: 1;
    }

    AIInsightsPanel .observation-item {
        width: 1fr;
    }

    AIInsightsPanel .recommendation-item {
        width: 1fr;
    }

    AIInsightsPanel .code-snippet {
        color: $text-muted;
        width: 1fr;
        margin-top: 1;
    }

    AIInsightsPanel .ai-disabled {
        color: $text-muted;
        text-style: italic;
        margin: 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Render initial layout with permanent AI warning banner."""
        with Vertical():
            yield Label("Analisis de IA", classes="panel-title")
            yield Static(
                "AVISO DE IA: La interpretación por Inteligencia Artificial es opcional, generativa y puede contener imprecisiones.",
                classes="ai-warning-banner",
            )
            yield Static(id="insights-content")

    def render_ai_analysis(
        self, ai_analysis: AIAnalysisResult | None, ai_error: str | None = None
    ) -> None:
        """Render AI analysis results, configuration placeholder, or execution error.

        Args:
            ai_analysis: AIAnalysisResult object or None
            ai_error: Detalle del error en la consulta de la IA, si existiera.
        """
        insights_content = self.query_one("#insights-content", Static)

        # Estado: IA configurada pero fallida
        if ai_error:
            insights_content.update(
                f"[red]Error en la consulta de IA:[/red]\n[red]{markup_escape(ai_error)}[/red]"
            )
            return

        # Estado: IA deshabilitada/no configurada
        if ai_analysis is None:
            insights_content.update(
                "IA no configurada\n"
                "[dim]Configure las variables de entorno QA_AI_BASE_URL y QA_AI_API_KEY para habilitar el análisis de IA.[/dim]"
            )
            return

        # Estado: Resultados de IA exitosos
        try:
            lines = self._format_ai_analysis(ai_analysis)
            insights_content.update("\n".join(lines))
        except Exception as e:
            insights_content.update(f"[red]Error al renderizar el análisis de IA: {e}[/red]")

    def set_loading_state(self) -> None:
        """Show loading state."""
        insights_content = self.query_one("#insights-content", Static)
        insights_content.update("[yellow]Analizando con IA...[/yellow]")

    def set_error(self, message: str = "Error al realizar el análisis de IA") -> None:
        """Show error state.

        Args:
            message: Error message to display
        """
        insights_content = self.query_one("#insights-content", Static)
        insights_content.update(f"[red]Error: {message}[/red]")

    def clear(self) -> None:
        """Clear analysis content."""
        insights_content = self.query_one("#insights-content", Static)
        insights_content.update("")

    @staticmethod
    def _format_ai_analysis(ai_analysis: AIAnalysisResult) -> list[str]:
        """Format AI analysis for display.

        Args:
            ai_analysis: AIAnalysisResult object

        Returns:
            List of formatted lines
        """
        lines = []

        # Summary
        if ai_analysis.summary:
            lines.append("[cyan]Resumen:[/cyan]")
            lines.append(ai_analysis.summary)
            lines.append("")

        # Observations
        if ai_analysis.observations:
            lines.append("[yellow]Observaciones:[/yellow]")
            for obs in ai_analysis.observations:
                severity = AIInsightsPanel._extract_severity(obs)
                icon = OBSERVATION_ICONS.get(severity, "•")
                lines.append(f"{icon} {obs}")
            lines.append("")

        # Recommendations
        if ai_analysis.recommendations:
            lines.append("[green]Recomendaciones:[/green]")
            for i, rec in enumerate(ai_analysis.recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")

        if ai_analysis.suggested_query:
            lines.append("[green]Consulta sugerida:[/green]")
            lines.append(f"```sql\n{ai_analysis.suggested_query}\n```")
            lines.append("")

        if not lines:
            lines.append("[dim]No hay analisis de IA disponible[/dim]")

        return lines

    @staticmethod
    def _extract_severity(text: str) -> str:
        """Extract severity level from observation text.

        Args:
            text: Observation text

        Returns:
            Severity level (CRITICAL, HIGH, MEDIUM, LOW)
        """
        text_upper = text.upper()
        if "CRITICAL" in text_upper or "CRITICO" in text_upper or "CRÍTICO" in text_upper:
            return "CRITICAL"
        elif "HIGH" in text_upper or "ALTO" in text_upper or "ERROR" in text_upper:
            return "HIGH"
        elif "MEDIUM" in text_upper or "MEDIO" in text_upper or "WARNING" in text_upper:
            return "MEDIUM"
        else:
            return "LOW"


class AIObservationsPanel(Container):
    """Legacy panel name - kept for backwards compatibility.

    Displays AI observations with severity-based styling.
    """

    DEFAULT_CSS = """
    AIObservationsPanel {
        width: 1fr;
        height: auto;
        border: solid $accent;
        padding: 1;
        background: $panel;
        overflow-y: auto;
        scrollbar-size-vertical: 0;
    }

    AIObservationsPanel:focus {
        border: solid $primary;
        scrollbar-size-vertical: 1;
    }

    AIObservationsPanel .section-title {
        text-style: bold;
        margin-bottom: 1;
    }

    AIObservationsPanel ListView {
        height: auto;
        border: solid $surface-lighten-1;
        overflow-y: auto;
        scrollbar-size-vertical: 0;
    }

    AIObservationsPanel ListView:focus {
        scrollbar-size-vertical: 1;
    }

    AIObservationsPanel ListItem {
        height: auto;
        padding: 0 1;
        margin-bottom: 0.5;
    }
    """

    def compose(self) -> ComposeResult:
        """Render initial layout."""
        yield Label("Observaciones de IA", classes="section-title")
        yield ListView(id="observations-list")

    def render_observations(self, observations: list[str]) -> None:
        """Render list of observations.

        Args:
            observations: List of observation strings
        """
        list_view = self.query_one("#observations-list", ListView)
        list_view.clear()

        if not observations:
            list_view.append(ListItem(Label("[dim]Sin observaciones[/dim]")))
            return
        for obs in observations:
            severity = AIInsightsPanel._extract_severity(obs)
            icon = OBSERVATION_ICONS.get(severity, "•")
            list_view.append(ListItem(Static(f"{icon} {obs}")))

    def set_loading_state(self) -> None:
        """Show loading state."""
        list_view = self.query_one("#observations-list", ListView)
        list_view.clear()
        list_view.append(ListItem(Label("[yellow]Analizando...[/yellow]")))

    def set_error(self) -> None:
        """Show error state."""
        list_view = self.query_one("#observations-list", ListView)
        list_view.clear()
        list_view.append(ListItem(Label("[red]Error al analizar[/red]")))


class AIRecommendationsPanel(Container):
    """Panel for displaying AI-powered recommendations with code snippets.

    Shows numbered recommendations with SQL code examples.
    """

    DEFAULT_CSS = """
    AIRecommendationsPanel {
        width: 1fr;
        height: auto;
        border: solid $accent;
        padding: 1;
        background: $panel;
        overflow-y: auto;
        scrollbar-size-vertical: 0;
    }

    AIRecommendationsPanel:focus {
        border: solid $primary;
        scrollbar-size-vertical: 1;
    }

    AIRecommendationsPanel .section-title {
        text-style: bold;
        margin-bottom: 1;
    }

    AIRecommendationsPanel ListView {
        height: auto;
        border: solid $surface-lighten-1;
        overflow-y: auto;
        scrollbar-size-vertical: 0;
    }

    AIRecommendationsPanel ListView:focus {
        scrollbar-size-vertical: 1;
    }

    AIRecommendationsPanel ListItem {
        height: auto;
        padding: 0 1;
        margin-bottom: 1;
    }

    AIRecommendationsPanel .rec-title {
        text-style: bold;
        margin-bottom: 0.5;
    }

    AIRecommendationsPanel .code-snippet {
        color: $text-muted;
        width: 1fr;
        margin-top: 0.5;
    }
    """

    def compose(self) -> ComposeResult:
        """Render initial layout."""
        yield Label("Recomendaciones de IA", classes="section-title")
        yield ListView(id="recommendations-list")

    def render_recommendations(self, recommendations: list[str]) -> None:
        """Render list of recommendations with code snippets.

        Args:
            recommendations: List of recommendation strings
        """
        list_view = self.query_one("#recommendations-list", ListView)
        list_view.clear()

        if not recommendations:
            list_view.append(ListItem(Label("[dim]Sin recomendaciones[/dim]")))
            return

        for idx, rec in enumerate(recommendations, start=1):
            # Check if recommendation contains SQL code
            if "```sql" in rec or "```" in rec:
                # Extract code snippet
                import re

                code_match = re.search(r"```(?:sql)?\n(.*?)\n```", rec, re.DOTALL)
                if code_match:
                    code = code_match.group(1)
                    rec_text = rec[: code_match.start()].strip()

                    sql_syntax = Syntax(
                        code,
                        "sql",
                        theme="monokai",
                        line_numbers=False,
                        word_wrap=True,
                    )

                    list_view.append(
                        ListItem(
                            Static(f"{idx}. {rec_text}", classes="rec-title"),
                            Static(sql_syntax, classes="code-snippet"),
                        )
                    )
                else:
                    list_view.append(ListItem(Static(f"{idx}. {rec}")))
            else:
                list_view.append(ListItem(Static(f"{idx}. {rec}")))

    def set_loading_state(self) -> None:
        """Show loading state."""
        list_view = self.query_one("#recommendations-list", ListView)
        list_view.clear()
        list_view.append(ListItem(Label("[yellow]Generando recomendaciones...[/yellow]")))

    def set_error(self) -> None:
        """Show error state."""
        list_view = self.query_one("#recommendations-list", ListView)
        list_view.clear()
        list_view.append(ListItem(Label("[red]Error al generar recomendaciones[/red]")))
