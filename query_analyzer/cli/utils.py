"""Utilidades para la interfaz CLI."""

from io import StringIO

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from query_analyzer.adapters import QueryAnalysisReport
from query_analyzer.adapters.serializer import ReportSerializer
from query_analyzer.cli.terminal_config import get_terminal_width
from query_analyzer.config import ProfileConfig

console = Console()


def truncate_text(text: str, max_width: int = 80) -> str:
    """Truncate text with ellipsis if too long."""
    if len(text) <= max_width:
        return text
    return text[: max_width - 1] + "…"


class OutputFormatter:
    """Formatea output para CLI con estilos."""

    @staticmethod
    def truncate_adaptive(
        text: str,
        max_width: int,
        min_visible: int = 0,
        suffix: str = "...",
    ) -> str:
        """Truncate text while preserving a useful visible prefix."""
        if len(text) <= max_width:
            return text
        visible = max(min_visible, max_width - len(suffix))
        return text[:visible] + suffix

    @staticmethod
    def mask_password(password: str, visible_chars: int = 2) -> str:
        """Enmascara un password en output.

        Args:
            password: Password a enmascarar
            visible_chars: Número de caracteres visibles al inicio

        Returns:
            Password enmascarado. Ej: "my**********"
        """
        if not password:
            return ""

        if len(password) <= visible_chars:
            return "*" * len(password)

        visible = password[:visible_chars]
        masked = "*" * (len(password) - visible_chars)
        return visible + masked

    @staticmethod
    def format_profile(
        name: str,
        profile: ProfileConfig,
        is_default: bool = False,
        mask_pwd: bool = True,
    ) -> str:
        """Formatea un perfil para mostrar.

        Returns:
            Cadena formateada del perfil
        """
        default_marker = " [bold green](default)[/bold green]" if is_default else ""
        password_display = (
            OutputFormatter.mask_password(profile.password or "") if mask_pwd else profile.password
        )

        return (
            f"[bold]{name}[/bold]{default_marker}\n"
            f"  Engine: {profile.engine}\n"
            f"  Host: {profile.host}:{profile.port}\n"
            f"  Database: {profile.database}\n"
            f"  Username: {profile.username}\n"
            f"  Password: {password_display}"
        )

    @staticmethod
    def print_success(message: str) -> None:
        """Imprime mensaje de exito con [OK]."""
        console.print(f"[green][OK][/green] {message}")

    @staticmethod
    def print_error(message: str) -> None:
        """Imprime mensaje de error con [ERROR]."""
        console.print(f"[red][ERROR][/red] {message}")

    @staticmethod
    def print_info(message: str) -> None:
        """Imprime mensaje informativo."""
        console.print(f"[blue][INFO][/blue] {message}")

    @staticmethod
    def print_warning(message: str) -> None:
        """Imprime mensaje de warning."""
        console.print(f"[yellow][WARN][/yellow] {message}")

    @staticmethod
    def create_profiles_table(
        profiles: dict[str, ProfileConfig], default_profile: str | None = None
    ) -> Table:
        """Crea una tabla para mostrar perfiles.

        Args:
            profiles: Diccionario de perfiles
            default_profile: Nombre del perfil default

        Returns:
            Tabla de rich
        """
        table = Table(title="Perfiles de Conexion", show_header=True, header_style="bold")
        table.add_column("Nombre", style="cyan")
        table.add_column("Engine", style="magenta")
        table.add_column("Host", style="green")
        table.add_column("Database", style="yellow")
        table.add_column("Usuario", style="blue")

        for name, profile in profiles.items():
            default_marker = "[DEFAULT]" if name == default_profile else ""
            table.add_row(
                f"{name} {default_marker}",
                profile.engine,
                f"{profile.host}:{profile.port}",
                profile.database,
                profile.username,
            )

        return table

    @staticmethod
    def format_report(
        report: QueryAnalysisReport,
        format: str = "rich",
        profile_name: str = "",
        is_default: bool = False,
        verbose: bool = False,
    ) -> str:
        """Format query analysis report.

        Args:
            report: QueryAnalysisReport to format
            format: Output format ('rich', 'json', 'text')
            profile_name: Profile name used (optional)
            is_default: Whether profile is default (optional)
            verbose: Verbose output (optional)

        Returns:
            Formatted report string
        """
        if format == "rich":
            return OutputFormatter._format_report_rich(report)
        elif format == "json":
            import json

            return json.dumps(
                report.to_dict() if hasattr(report, "to_dict") else str(report), indent=2
            )
        elif format == "markdown":
            return ReportSerializer.to_markdown(report)
        return str(report)

    @staticmethod
    def _format_report_rich(report: QueryAnalysisReport) -> str:
        """Format observed engine data for a terminal."""
        width = get_terminal_width()
        header_content = (
            f"[cyan]Motor:[/cyan] [bold]{report.engine.upper()}[/bold]\n"
            f"[cyan]Tiempo de ejecucion:[/cyan] {report.execution_time_ms:.2f} ms\n"
            f"[cyan]Plan:[/cyan] {report.plan_summary or 'No disponible'}\n"
            f"[cyan]Consulta:[/cyan] {OutputFormatter.truncate_adaptive(report.query, width - 12)}"
        )
        buffer = StringIO()
        render_console = Console(file=buffer, force_terminal=True, width=width)
        render_console.print(
            Panel(header_content, title="DATOS OBSERVADOS DE EJECUCION", expand=True)
        )

        if report.metrics:
            table = Table(show_header=True, header_style="bold")
            table.add_column("Metric")
            table.add_column("Observed value")
            for key, value in report.metrics.items():
                table.add_row(str(key), str(value))
            render_console.print(table)

        if report.ai_analysis:
            render_console.print(
                Panel(report.ai_analysis.summary, title="ANALISIS DE IA", expand=True)
            )

        return buffer.getvalue().rstrip()

    @staticmethod
    def print_report(
        report: QueryAnalysisReport,
        format: str = "rich",
        profile_name: str = "",
        is_default: bool = False,
        verbose: bool = False,
        console_instance: Console | None = None,
    ) -> None:
        """Print formatted report (v2.0.0 - no score, AI-ready).

        Args:
            report: QueryAnalysisReport to print
            format: Output format ('rich', 'json', 'text')
            profile_name: Profile name used (optional)
            is_default: Whether profile is default (optional)
            verbose: Verbose output (optional)
            console_instance: Rich console instance to use (optional)
        """
        target_console = console_instance if console_instance else console

        if format == "rich":
            # Header
            query_display = truncate_text(report.query, max_width=100)

            target_console.print(
                "[bold cyan]--- REPORTE DE ANALISIS DE CONSULTA (v2.0.0) ---[/bold cyan]"
            )
            target_console.print(f"[cyan]Motor:[/cyan] [bold]{report.engine}[/bold]")
            target_console.print(
                f"[cyan]Tiempo de ejecucion:[/cyan] [bold]{report.execution_time_ms:.2f} ms[/bold]"
            )
            target_console.print(f"[cyan]Consulta:[/cyan] {query_display}")
            if report.plan_summary:
                target_console.print(f"[cyan]Resumen del plan:[/cyan] {report.plan_summary}")
            target_console.print()

            # AI Analysis section (if available)
            if report.ai_analysis:
                target_console.print()
                target_console.print("[bold green]ANALISIS DE IA[/bold green]")

                ai = report.ai_analysis
                if ai.summary:
                    target_console.print(f"[green]Resumen:[/green] {ai.summary}")

                if ai.observations:
                    target_console.print("[green]Observaciones:[/green]")
                    for obs in ai.observations:
                        target_console.print(f"  • {obs}")

                if ai.recommendations:
                    target_console.print("[green]Recomendaciones de IA:[/green]")
                    for i, rec in enumerate(ai.recommendations, 1):
                        target_console.print(f"  {i}. {rec}")

                if ai.suggested_query:
                    target_console.print("[green]Consulta sugerida:[/green]")
                    target_console.print(ai.suggested_query)

                target_console.print()

            # Metrics section
            if report.metrics:
                target_console.print()
                target_console.print("[bold blue]METRICS[/bold blue]")
                metrics_table = Table(show_header=True, header_style="bold")
                metrics_table.add_column("Metric", width=20)
                metrics_table.add_column("Value", width=15)
                for key, value in list(report.metrics.items())[:5]:
                    metrics_table.add_row(key, str(value))
                target_console.print(metrics_table)

            target_console.print()
            target_console.print(
                "[dim]Nota: el analisis de IA esta disponible si QA_AI_BASE_URL esta configurada[/dim]"
            )
        elif format == "json":
            import json

            output = json.dumps(
                report.to_dict() if hasattr(report, "to_dict") else str(report),
                indent=2,
            )
            target_console.print(output)
        elif format == "markdown":
            target_console.print(ReportSerializer.to_markdown(report))
        else:
            target_console.print(str(report))
