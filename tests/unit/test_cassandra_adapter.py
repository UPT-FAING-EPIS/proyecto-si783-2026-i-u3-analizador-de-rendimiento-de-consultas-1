"""Tests for Cassandra trace-based reporting."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from query_analyzer.adapters.exceptions import QueryAnalysisError
from query_analyzer.adapters.models import ConnectionConfig
from query_analyzer.adapters.nosql.cassandra import CassandraAdapter


@pytest.fixture
def adapter() -> CassandraAdapter:
    instance = CassandraAdapter(
        ConnectionConfig(
            engine="cassandra",
            host="localhost",
            port=9042,
            database="app",
            username=None,
            password=None,
        )
    )
    instance._is_connected = True
    instance._session = MagicMock()
    instance._schema_cache["users"] = {
        "partition_keys": ["id"],
        "clustering_keys": [],
    }
    return instance


def test_extract_table_name() -> None:
    instance = CassandraAdapter(
        ConnectionConfig(engine="cassandra", host="localhost", database="app")
    )
    assert instance._extract_table_name("SELECT * FROM app.users WHERE id=1") == "users"


def test_execute_explain_returns_trace_metrics(adapter: CassandraAdapter) -> None:
    event = SimpleNamespace(
        event_id="1",
        timestamp="2026-06-10T10:00:00Z",
        source="127.0.0.1",
        thread_id="worker-1",
        activity="Executing single-partition query",
        source_elapsed=120,
    )
    trace = SimpleNamespace(
        events=[event],
        duration=2500,
        client="127.0.0.1",
        coordinator="127.0.0.1",
    )
    result = MagicMock()
    result.get_query_trace.return_value = trace
    adapter._session.prepare.return_value = MagicMock()
    adapter._session.execute.return_value = result

    report = adapter.execute_explain("SELECT * FROM users WHERE id=1")

    assert report.engine == "cassandra"
    assert report.execution_time_ms == 2.5
    assert report.metrics["trace_events_count"] == 1
    assert report.plan_tree is not None
    assert "score" not in report.model_dump()


def test_execute_explain_rejects_non_select(adapter: CassandraAdapter) -> None:
    with pytest.raises(QueryAnalysisError, match="Only SELECT"):
        adapter.execute_explain("DELETE FROM users WHERE id=1")


def test_not_connected_is_rejected() -> None:
    instance = CassandraAdapter(
        ConnectionConfig(engine="cassandra", host="localhost", database="app")
    )
    with pytest.raises(QueryAnalysisError, match="Not connected"):
        instance.execute_explain("SELECT * FROM users")
