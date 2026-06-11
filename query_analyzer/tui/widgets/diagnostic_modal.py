"""Modal de diagnóstico de conexiones para la TUI."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

from query_analyzer.core.connection_diagnostics import ConnectionDiagnostic


class DiagnosticModal(ModalScreen[None]):
    """Pantalla modal que muestra los resultados detallados del diagnóstico de conexión."""

    DEFAULT_CSS = """
    DiagnosticModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }

    DiagnosticModal > Container {
        width: 75;
        max-width: 90%;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    DiagnosticModal .title {
        text-style: bold;
        font-size: 1.2;
        margin-bottom: 1;
        content-align: center middle;
        width: 100%;
    }

    DiagnosticModal .status-bar {
        padding: 1;
        margin-bottom: 1;
        text-style: bold;
        content-align: center middle;
        width: 100%;
    }

    DiagnosticModal .status-connected {
        background: $success;
        color: $text;
    }

    DiagnosticModal .status-error {
        background: $error;
        color: $text;
    }

    DiagnosticModal .checks-container {
        height: auto;
        max-height: 12;
        border: solid $surface-lighten-1;
        padding: 1;
        margin-bottom: 1;
        background: $panel;
    }

    DiagnosticModal .check-row {
        height: auto;
        margin-bottom: 0;
        width: 100%;
    }

    DiagnosticModal .check-success {
        color: $success;
    }

    DiagnosticModal .check-failed {
        color: $error;
    }

    DiagnosticModal .check-skipped {
        color: $text-muted;
    }

    DiagnosticModal .recommendations {
        background: $surface-lighten-1;
        padding: 1;
        margin-bottom: 1;
        height: auto;
        width: 100%;
    }

    DiagnosticModal .rec-title {
        text-style: bold;
        color: $warning;
        margin-bottom: 1;
    }

    DiagnosticModal .tech-detail-container {
        background: $surface-darken-1;
        color: $text-muted;
        font-size: 0.9;
        padding: 1;
        margin-bottom: 1;
        height: auto;
        max-height: 8;
        width: 100%;
    }

    DiagnosticModal .close-container {
        align: center middle;
        height: auto;
        width: 100%;
    }

    DiagnosticModal Button {
        margin-top: 1;
    }
    """

    def __init__(self, diagnostic: ConnectionDiagnostic) -> None:
        """Inicializa el modal con el reporte de diagnóstico.

        Args:
            diagnostic: Reporte de diagnóstico de conexión.
        """
        super().__init__()
        self._diagnostic = diagnostic

    def compose(self) -> ComposeResult:
        diag = self._diagnostic
        is_ok = diag.status == "connected"
        status_class = "status-connected" if is_ok else "status-error"
        status_text = (
            f"CONECTADO - {diag.safe_message}"
            if is_ok
            else f"ERROR ({diag.status.upper()}) - {diag.safe_message}"
        )

        with Container():
            yield Label(
                f"Diagnóstico de Perfil: {diag.profile_name} ({diag.engine.upper()})",
                classes="title",
            )
            yield Static(status_text, classes=f"status-bar {status_class}")

            with Vertical(classes="checks-container"):
                for check in diag.checks:
                    if check.status == "success":
                        status_symbol = "✓"
                        symbol_class = "check-success"
                    elif check.status == "failed":
                        status_symbol = "✗"
                        symbol_class = "check-failed"
                    else:
                        status_symbol = "-"
                        symbol_class = "check-skipped"

                    duration_str = (
                        f"({check.duration_ms:.1f}ms)" if check.status != "skipped" else ""
                    )
                    yield Label(
                        f"[{symbol_class}]{status_symbol}[/{symbol_class}] "
                        f"[bold]{check.name}[/bold]: {check.message} {duration_str}",
                        classes="check-row",
                    )

            if not is_ok:
                rec_text = self._get_recommendation(diag.status)
                with Vertical(classes="recommendations"):
                    yield Label("Solución Sugerida:", classes="rec-title")
                    yield Label(rec_text)

            if diag.technical_detail:
                with Vertical(classes="tech-detail-container"):
                    yield Label("[bold]Detalle Técnico (Sanitizado):[/bold]")
                    yield Label(diag.technical_detail)

            with Horizontal(classes="close-container"):
                yield Button("Cerrar", variant="default", id="btn-close")

    def _get_recommendation(self, status: str) -> str:
        recommendations = {
            "configuration_error": (
                "Verifique los parámetros del perfil. Asegúrese de que el host, puerto "
                "y base de datos tengan valores correctos y no estén vacíos."
            ),
            "service_unreachable": (
                "El host o puerto es inaccesible. Verifique que la base de datos esté encendida, "
                "acepte conexiones externas y que ningún firewall o contenedor de Docker esté "
                "bloqueando el puerto."
            ),
            "timeout": (
                "La conexión tardó demasiado tiempo en responder. Verifique la latencia "
                "de red o que el servidor no esté sobrecargado."
            ),
            "authentication_failed": (
                "El usuario o la contraseña proporcionados no son correctos. "
                "Verifique sus credenciales de acceso."
            ),
            "database_missing": (
                "La base de datos especificada no existe en el servidor. Verifique que el "
                "nombre esté bien escrito o cree la base de datos."
            ),
        }
        return recommendations.get(
            status,
            "Ocurrió un error inesperado. Revise el detalle técnico para más información.",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close":
            self.dismiss()
