"""Unit tests for AnalysisScreen key bindings and keyboard actions."""

from types import SimpleNamespace

from query_analyzer.tui.screens.analysis_screen import AnalysisScreen


def test_analysis_screen_bindings_include_h_l_and_uppercase_h() -> None:
    """Analysis screen should expose combined tab nav and uppercase H history."""
    all_bindings = {(binding.key, binding.action) for binding in AnalysisScreen.BINDINGS}
    assert ("h,ctrl+left", "previous_tab") in all_bindings
    assert ("l,ctrl+right", "next_tab") in all_bindings
    assert ("H", "show_history") in all_bindings


def test_action_next_tab_moves_to_following_tab(monkeypatch) -> None:
    """Next tab action should advance active tab in cycle."""
    screen = AnalysisScreen("demo")
    tabbed = SimpleNamespace(active="tab-metrics")
    monkeypatch.setattr(screen, "_get_tabbed_content", lambda: tabbed)

    screen.action_next_tab()

    assert tabbed.active == "tab-plan"


def test_action_previous_tab_moves_to_previous_tab(monkeypatch) -> None:
    """Previous tab action should move active tab backward in cycle."""
    screen = AnalysisScreen("demo")
    tabbed = SimpleNamespace(active="tab-summary")
    monkeypatch.setattr(screen, "_get_tabbed_content", lambda: tabbed)

    screen.action_previous_tab()

    assert tabbed.active == "tab-ai"


def test_action_show_history_uses_history_screen_when_records_exist(monkeypatch) -> None:
    """History action should open history modal when records exist."""
    screen = AnalysisScreen("demo")
    fake_app = SimpleNamespace(push_screen=lambda *_args, **_kwargs: None)
    monkeypatch.setattr(AnalysisScreen, "app", property(lambda _self: fake_app))

    class _FakeHistoryManager:
        def get_all(self) -> list[int]:
            return [1]

    pushed = {"called": False}

    def _push_screen(_screen: object, _callback: object) -> None:
        pushed["called"] = True

    fake_app.push_screen = _push_screen

    monkeypatch.setattr(
        "query_analyzer.tui.screens.analysis_screen.get_history_manager",
        lambda: _FakeHistoryManager(),
    )

    screen.action_show_history()

    assert pushed["called"] is True


def test_action_select_tab_summary_sets_active_tab(monkeypatch) -> None:
    """Summary action should select summary tab."""
    screen = AnalysisScreen("demo")
    tabbed = SimpleNamespace(active="tab-ai")
    monkeypatch.setattr(screen, "_get_tabbed_content", lambda: tabbed)

    screen.action_select_tab_summary()

    assert tabbed.active == "tab-summary"


def test_action_select_tab_metrics_sets_active_tab(monkeypatch) -> None:
    """Metrics action should select metrics tab."""
    screen = AnalysisScreen("demo")
    tabbed = SimpleNamespace(active="tab-summary")
    monkeypatch.setattr(screen, "_get_tabbed_content", lambda: tabbed)

    screen.action_select_tab_metrics()

    assert tabbed.active == "tab-metrics"


def test_action_select_tab_plan_sets_active_tab(monkeypatch) -> None:
    """Plan action should select plan tab."""
    screen = AnalysisScreen("demo")
    tabbed = SimpleNamespace(active="tab-metrics")
    monkeypatch.setattr(screen, "_get_tabbed_content", lambda: tabbed)

    screen.action_select_tab_plan()

    assert tabbed.active == "tab-plan"


def test_action_select_tab_ai_sets_active_tab(monkeypatch) -> None:
    """AI action should select AI tab."""
    screen = AnalysisScreen("demo")
    tabbed = SimpleNamespace(active="tab-plan")
    monkeypatch.setattr(screen, "_get_tabbed_content", lambda: tabbed)

    screen.action_select_tab_ai()

    assert tabbed.active == "tab-ai"
