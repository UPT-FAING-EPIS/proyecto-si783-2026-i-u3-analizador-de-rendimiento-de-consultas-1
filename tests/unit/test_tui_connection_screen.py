"""Unit tests for TUI connection screen behavior."""

from unittest.mock import MagicMock

from query_analyzer.tui.app import ConnectionScreen
from query_analyzer.tui.connection_state import ConnectionStatus
from query_analyzer.tui.widgets.profile_selector import ProfileAction


class _FakeManager:
    def __init__(self, status: ConnectionStatus) -> None:
        self._status = status

    def status_for_profile(self, profile_name: str) -> ConnectionStatus:
        return self._status


def _build_screen_with_dependencies(
    monkeypatch,
    status: ConnectionStatus,
) -> tuple[ConnectionScreen, MagicMock, MagicMock]:
    fake_manager = _FakeManager(status)
    monkeypatch.setattr(
        "query_analyzer.tui.app.ConnectionManager.get",
        lambda: fake_manager,
    )

    screen = ConnectionScreen()
    status_bar = MagicMock()
    monkeypatch.setattr(screen, "query_one", lambda *_args, **_kwargs: status_bar)

    fake_app = MagicMock()
    setattr(screen, "_fake_app", fake_app)
    monkeypatch.setattr(
        ConnectionScreen,
        "app",
        property(lambda s: s._fake_app),
        raising=False,
    )
    return screen, status_bar, fake_app


def test_analyze_allows_navigation_when_profile_connected(monkeypatch) -> None:
    """Connected profiles should open analysis screen."""
    screen, _status_bar, fake_app = _build_screen_with_dependencies(
        monkeypatch, ConnectionStatus.CONNECTED
    )

    screen.on_profile_action(ProfileAction("analyze", "demo"))

    fake_app.push_screen.assert_called_once()


def test_analyze_blocks_navigation_when_profile_disconnected(monkeypatch) -> None:
    """Disconnected profiles should not open analysis screen."""
    screen, status_bar, fake_app = _build_screen_with_dependencies(
        monkeypatch, ConnectionStatus.DISCONNECTED
    )

    screen.on_profile_action(ProfileAction("analyze", "demo"))

    fake_app.push_screen.assert_not_called()
    status_bar.update.assert_called_once()


def test_analyze_blocks_navigation_when_profile_error(monkeypatch) -> None:
    """Profiles in error state should not open analysis screen."""
    screen, status_bar, fake_app = _build_screen_with_dependencies(
        monkeypatch, ConnectionStatus.ERROR
    )

    screen.on_profile_action(ProfileAction("analyze", "demo"))

    fake_app.push_screen.assert_not_called()
    status_bar.update.assert_called_once()
