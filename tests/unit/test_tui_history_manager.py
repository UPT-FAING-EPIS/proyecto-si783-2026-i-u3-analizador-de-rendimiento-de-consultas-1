"""Unit tests for persistent TUI history manager."""

from pathlib import Path

from query_analyzer.adapters.models import QueryAnalysisReport
from query_analyzer.tui.history_manager import HistoryManager


def _report(query: str, engine: str = "postgresql") -> QueryAnalysisReport:
    return QueryAnalysisReport(
        engine=engine,
        query=query,
        execution_time_ms=1.25,
    )


def test_history_manager_persists_and_reloads_by_profile(tmp_path: Path) -> None:
    """Should persist records to profile file and reload them."""
    manager = HistoryManager(storage_dir=tmp_path / "history")
    manager.add("SELECT 1", _report("SELECT 1"), "profile_a")

    reloaded = HistoryManager(storage_dir=tmp_path / "history")
    records = reloaded.get_all_for_profile("profile_a")

    assert len(records) == 1
    assert records[0].query == "SELECT 1"


def test_history_manager_keeps_profiles_separated(tmp_path: Path) -> None:
    """Should store and retrieve records independently per profile."""
    manager = HistoryManager(storage_dir=tmp_path / "history")
    manager.add("SELECT * FROM users", _report("SELECT * FROM users"), "profile_a")
    manager.add("SELECT * FROM orders", _report("SELECT * FROM orders"), "profile_b")

    records_a = manager.get_all_for_profile("profile_a")
    records_b = manager.get_all_for_profile("profile_b")

    assert len(records_a) == 1
    assert len(records_b) == 1
    assert records_a[0].query == "SELECT * FROM users"
    assert records_b[0].query == "SELECT * FROM orders"


def test_history_manager_clear_profile_only_removes_target(tmp_path: Path) -> None:
    """clear_profile should remove only the target profile file and records."""
    manager = HistoryManager(storage_dir=tmp_path / "history")
    manager.add("SELECT 1", _report("SELECT 1"), "profile_a")
    manager.add("SELECT 2", _report("SELECT 2"), "profile_b")

    manager.clear_profile("profile_a")

    assert manager.get_all_for_profile("profile_a") == []
    assert len(manager.get_all_for_profile("profile_b")) == 1
