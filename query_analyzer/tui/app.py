"""Query Analyzer TUI - Main App.

Textual-based terminal interface for connection profile management.
"""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Thread
from typing import TYPE_CHECKING

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Static

from query_analyzer.tui.connection_state import ConnectionManager, ConnectionStatus
from query_analyzer.tui.screens.analysis_screen import AnalysisScreen
from query_analyzer.tui.widgets.connection_form import ConnectionForm
from query_analyzer.tui.widgets.profile_selector import ProfileAction, ProfileSelector

if TYPE_CHECKING:
    from query_analyzer.core.connection_diagnostics import ConnectionDiagnostic


class StatusBar(Static):
    """Barra de estado inferior."""

    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        background: $surface-darken-1;
        content-align: center middle;
    }
    """

    def __init__(self) -> None:
        super().__init__("", id="status-bar")
        self._manager = ConnectionManager.get()

    def update_status(self) -> None:
        counts = self._manager.status_counts()
        connected = counts[ConnectionStatus.CONNECTED]
        connecting = counts[ConnectionStatus.CONNECTING]
        errors = counts[ConnectionStatus.ERROR]
        disconnected = counts[ConnectionStatus.DISCONNECTED]

        parts = [f"[green]{connected} conectados[/green]"]
        if connecting:
            parts.append(f"[yellow]{connecting} probando[/yellow]")
        if errors:
            parts.append(f"[red]{errors} con error[/red]")
        if disconnected:
            parts.append(f"{disconnected} sin probar")

        self.update(" | ".join(parts))


class DeleteConfirm(ModalScreen[bool]):
    """Pantalla de confirmación de eliminación."""

    DEFAULT_CSS = """
    DeleteConfirm {
        align: center middle;
    }

    DeleteConfirm > Container {
        width: 40;
        height: auto;
        border: solid $error;
        padding: 1 2;
    }

    DeleteConfirm .message {
        margin-bottom: 2;
    }

    DeleteConfirm .buttons {
        height: auto;
    }
    """

    def __init__(self, profile_name: str, on_confirm: Callable[[], None]) -> None:
        super().__init__()
        self._profile_name = profile_name
        self._on_confirm = on_confirm

    def compose(self) -> ComposeResult:
        with Container(classes="confirm-container"):
            yield Static(
                f"¿Eliminar perfil '{self._profile_name}'?",
                classes="message",
            )
            with Container(classes="buttons"):
                yield Button("Cancelar", variant="default", id="btn-cancel")
                yield Button("Eliminar", variant="error", id="btn-confirm")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(False)
        elif event.button.id == "btn-confirm":
            self._on_confirm()
            self.dismiss(True)


class ConnectionScreen(Container):
    """Pantalla principal de selección de perfiles."""

    def __init__(self) -> None:
        super().__init__(id="connection-screen")
        self._manager = ConnectionManager.get()

    def compose(self) -> ComposeResult:
        yield ProfileSelector()
        yield StatusBar()

    def on_mount(self) -> None:
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.update_status()
        self._start_initial_probe()

    def on_profile_action(self, event: ProfileAction) -> None:
        action = event.action
        profile_name = event.profile_name

        if action == "add":
            self.app.push_screen(ConnectionForm(), self._on_form_return)
        elif action == "edit" and profile_name:
            self.app.push_screen(
                ConnectionForm(edit_profile_name=profile_name), self._on_form_return
            )
        elif action == "delete" and profile_name:
            self._delete_profile(profile_name)
        elif action == "diagnose" and profile_name:
            self._run_diagnostics_and_show(profile_name)
        elif action == "analyze" and profile_name:
            profile_status = self._manager.status_for_profile(profile_name)
            status_bar = self.query_one("#status-bar", StatusBar)

            if profile_status != ConnectionStatus.CONNECTED:
                if profile_status == ConnectionStatus.CONNECTING:
                    status_bar.update(
                        f"[yellow]El perfil '{profile_name}' aun se esta conectando[/yellow]"
                    )
                elif profile_status == ConnectionStatus.ERROR:
                    status_bar.update(
                        f"[red]El perfil '{profile_name}' tiene estado error."
                        " Solo se puede analizar con estado conectado[/red]"
                    )
                else:
                    status_bar.update(
                        f"[yellow]El perfil '{profile_name}' esta desconectado."
                        " Solo se puede analizar con estado conectado[/yellow]"
                    )
                return

            self.app.push_screen(AnalysisScreen(profile_name))

    def _on_form_return(self, saved: bool | None) -> None:
        if saved:
            selector = self.query_one(ProfileSelector)
            selector.reload_profiles()
            status_bar = self.query_one("#status-bar", StatusBar)
            status_bar.update_status()

    def _delete_profile(self, name: str) -> None:
        def on_confirm() -> None:
            self._manager.delete_profile(name)
            selector = self.query_one(ProfileSelector)
            selector.reload_profiles()
            status_bar = self.query_one("#status-bar", StatusBar)
            status_bar.update_status()

        self.app.push_screen(DeleteConfirm(name, on_confirm))

    def _run_diagnostics_and_show(self, name: str) -> None:
        if self._manager.status_for_profile(name) == ConnectionStatus.CONNECTING:
            return

        self._manager.mark_connecting(name)
        self._refresh_ui_status()

        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.update(f"[yellow]Ejecutando diagnóstico para '{name}'...[/yellow]")

        def run() -> None:
            try:
                config_mgr = self._manager.config_manager
                connection_config = config_mgr.get_connection_config(name)
                from query_analyzer.core.connection_diagnostics import ConnectionDiagnosticsService

                diagnostic = ConnectionDiagnosticsService.run_diagnostics(name, connection_config)

                self._manager.set_diagnostic(name, diagnostic)

                if diagnostic.status == "connected":
                    self._manager.set_profile_status(name, ConnectionStatus.CONNECTED)
                else:
                    self._manager.set_profile_status(
                        name, ConnectionStatus.ERROR, diagnostic.safe_message
                    )

                self.app.call_from_thread(self._show_diagnostic_modal, diagnostic)
            except Exception as e:
                self.app.call_from_thread(
                    status_bar.update, f"[red]Error al diagnosticar: {e}[/red]"
                )
                self._manager.set_profile_status(name, ConnectionStatus.ERROR, str(e))
            finally:
                self.app.call_from_thread(self._refresh_ui_status)

        Thread(target=run, daemon=True).start()

    def _show_diagnostic_modal(self, diagnostic: ConnectionDiagnostic) -> None:
        from query_analyzer.tui.widgets.diagnostic_modal import DiagnosticModal

        self.app.push_screen(DiagnosticModal(diagnostic))

    def _start_initial_probe(self) -> None:
        probe_thread = Thread(target=self._probe_all_profiles_background, daemon=True)
        probe_thread.start()

    def _probe_all_profiles_background(self) -> None:
        profile_names = list(self._manager.list_profiles())
        if not profile_names:
            return

        for name in profile_names:
            self._manager.mark_connecting(name)
        self.app.call_from_thread(self._refresh_ui_status)

        worker_count = min(8, len(profile_names))
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = {
                executor.submit(self._manager.probe_profile, name): name for name in profile_names
            }
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    pass
                self.app.call_from_thread(self._refresh_ui_status)

    def _refresh_ui_status(self) -> None:
        selector = self.query_one(ProfileSelector)
        selector.reload_profiles()
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.update_status()


class QueryAnalyzerApp(App):
    """App principal de Query Analyzer TUI."""

    TITLE = "Query Analyzer"
    SUB_TITLE = "Gestión de conexiones"
    CSS_PATH = None

    DEFAULT_CSS = """
    Screen {
        background: $background;
    }

    #connection-screen {
        align: center middle;
    }

    #connection-screen > ProfileSelector {
        width: 1fr;
        max-width: 120;
        height: auto;
        background: $surface;
    }

    #main-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        background: $primary;
        color: $text;
        padding: 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "Salir"),
        ("c", "app.pop_screen", "Cancelar"),
        ("d", "diagnose_selected", "Diagnóstico"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._manager = ConnectionManager.get()

    def compose(self) -> ComposeResult:
        yield Header()
        yield ConnectionScreen()
        yield Footer()

    def on_mount(self) -> None:
        pass

    def action_diagnose_selected(self) -> None:
        """Acción de teclado para diagnosticar el perfil seleccionado."""
        try:
            connection_screen = self.query_one(ConnectionScreen)
            selector = connection_screen.query_one(ProfileSelector)
            selected = selector.selected_profile
            if selected:
                connection_screen.post_message(ProfileAction("diagnose", selected))
        except Exception:
            pass


def run() -> None:
    """Entry point para ejecutar la TUI."""
    app = QueryAnalyzerApp()
    app.run()


if __name__ == "__main__":
    run()
