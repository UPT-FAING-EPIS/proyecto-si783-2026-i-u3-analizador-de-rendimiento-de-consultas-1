"""Unit tests for TUI profile selector widget."""

from unittest.mock import MagicMock

from query_analyzer.tui.connection_state import ConnectionStatus
from query_analyzer.tui.widgets.profile_selector import ProfileSelector


class _FakeConnectionManager:
    default_profile_name = None

    def __init__(self, status: ConnectionStatus = ConnectionStatus.DISCONNECTED) -> None:
        self._status = status

    def list_profiles(self) -> dict[str, object]:
        return {}

    def status_for_profile(self, profile_name: str) -> ConnectionStatus | None:
        return self._status


def test_profile_selector_empty_state_row_matches_columns(monkeypatch) -> None:
    """Empty profile list should render a row with the same number of columns."""
    fake_manager = _FakeConnectionManager()
    monkeypatch.setattr(
        "query_analyzer.tui.widgets.profile_selector.ConnectionManager.get",
        lambda: fake_manager,
    )

    selector = ProfileSelector()
    table = MagicMock()
    monkeypatch.setattr(selector, "query_one", lambda *_args, **_kwargs: table)

    selector._refresh_profile_list()

    assert table.add_column.call_count == 4
    table.add_row.assert_called_once_with("-", "No hay perfiles", "", "desconectado")
    table.clear.assert_called_once_with(columns=False)


def test_is_selected_profile_connected_true_when_status_connected(monkeypatch) -> None:
    """Analyze should be available only for connected profile."""
    fake_manager = _FakeConnectionManager(status=ConnectionStatus.CONNECTED)
    monkeypatch.setattr(
        "query_analyzer.tui.widgets.profile_selector.ConnectionManager.get",
        lambda: fake_manager,
    )

    selector = ProfileSelector()
    selector._selected_profile = "demo"

    assert selector._is_selected_profile_connected() is True


def test_update_analyze_button_disables_for_disconnected(monkeypatch) -> None:
    """Analyze button should be disabled when profile is disconnected."""
    fake_manager = _FakeConnectionManager(status=ConnectionStatus.DISCONNECTED)
    monkeypatch.setattr(
        "query_analyzer.tui.widgets.profile_selector.ConnectionManager.get",
        lambda: fake_manager,
    )

    selector = ProfileSelector()
    selector._selected_profile = "demo"

    analyze_button = MagicMock()
    monkeypatch.setattr(selector, "query_one", lambda *_args, **_kwargs: analyze_button)

    selector._update_analyze_button_state()

    assert analyze_button.disabled is True
