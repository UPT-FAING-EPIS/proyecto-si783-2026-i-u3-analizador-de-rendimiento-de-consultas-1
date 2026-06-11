"""Tests unitarios para la integración de diagnóstico en la TUI."""

from unittest.mock import MagicMock, patch

from query_analyzer.core.connection_diagnostics import ConnectionDiagnostic, DiagnosticCheck
from query_analyzer.tui.app import ConnectionScreen
from query_analyzer.tui.widgets.diagnostic_modal import DiagnosticModal
from query_analyzer.tui.widgets.profile_selector import ProfileAction


def test_diagnostic_modal_init_and_recommendations() -> None:
    """Verifica la inicialización de DiagnosticModal y sus recomendaciones."""
    diag = ConnectionDiagnostic(
        profile_name="postgres_prod",
        engine="postgresql",
        endpoint="prod-db:5432",
        status="connected",
        checks=[
            DiagnosticCheck(
                name="Validación de Configuración",
                status="success",
                message="Configuración válida",
                duration_ms=1.5,
            )
        ],
        duration_ms=1.5,
        safe_message="Conexión exitosa",
    )

    modal = DiagnosticModal(diag)
    assert modal._diagnostic == diag

    # Verificar recomendaciones correctas según el estado
    assert "parámetros del perfil" in modal._get_recommendation("configuration_error")
    assert "inaccesible" in modal._get_recommendation("service_unreachable")
    assert "credenciales de acceso" in modal._get_recommendation("authentication_failed")
    assert "no existe en el servidor" in modal._get_recommendation("database_missing")
    assert "tardó demasiado tiempo" in modal._get_recommendation("timeout")
    assert "inesperado" in modal._get_recommendation("unknown_error")


def test_diagnostic_modal_button_dismiss() -> None:
    """Verifica que el modal se cierre al presionar el botón."""
    diag = ConnectionDiagnostic(
        profile_name="mysql_local",
        engine="mysql",
        endpoint="localhost:3306",
        status="authentication_failed",
        checks=[],
        duration_ms=0.0,
        safe_message="Error",
    )

    modal = DiagnosticModal(diag)
    modal.dismiss = MagicMock()

    event = MagicMock()
    event.button.id = "btn-close"

    modal.on_button_pressed(event)
    modal.dismiss.assert_called_once()


@patch("query_analyzer.tui.app.Thread")
def test_connection_screen_diagnose_action(mock_thread: MagicMock, monkeypatch) -> None:
    """Verifica que la acción 'diagnose' en ConnectionScreen inicie el hilo de diagnóstico."""
    # Creamos ConnectionScreen
    screen = ConnectionScreen()
    status_bar = MagicMock()
    monkeypatch.setattr(screen, "query_one", lambda *_args, **_kwargs: status_bar)

    # Postear la acción de diagnosticar
    screen.on_profile_action(ProfileAction("diagnose", "postgres"))

    # Debe actualizar la barra de estado e iniciar el hilo de background
    status_bar.update.assert_called_once()
    assert "Ejecutando diagnóstico" in status_bar.update.call_args[0][0]
    mock_thread.assert_called_once()
