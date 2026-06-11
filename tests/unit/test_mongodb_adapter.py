"""Tests for MongoDB factual reports."""

from unittest.mock import MagicMock

from query_analyzer.adapters.models import ConnectionConfig
from query_analyzer.adapters.nosql.mongodb import MongoDBAdapter


def test_execute_explain_returns_observed_plan() -> None:
    adapter = MongoDBAdapter(
        ConnectionConfig(
            engine="mongodb",
            host="localhost",
            database="app",
            username="user",
            password="pass",
        )
    )
    adapter._is_connected = True
    adapter._db = MagicMock()
    collection = adapter._db.__getitem__.return_value
    cursor = MagicMock()
    collection.find.return_value = cursor
    cursor.limit.return_value = cursor
    cursor.explain.return_value = {
        "queryPlanner": {"winningPlan": {"stage": "COLLSCAN"}},
        "executionStats": {
            "executionTimeMillis": 2,
            "nReturned": 5,
            "totalDocsExamined": 10,
            "totalKeysExamined": 0,
        },
    }

    report = adapter.execute_explain('{"collection":"users","filter":{"active":true}}')
    assert report.engine == "mongodb"
    assert report.plan_summary
    assert report.raw_plan is not None
    assert "warnings" not in report.model_dump()
