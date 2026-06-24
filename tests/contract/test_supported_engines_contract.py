"""Cross-engine contracts for every adapter supported by Query Analyzer."""

from typing import Any

import pytest

from query_analyzer.adapters import AdapterRegistry, BaseAdapter, ConnectionConfig

SUPPORTED_ENGINES = {
    "cassandra",
    "cockroachdb",
    "dynamodb",
    "elasticsearch",
    "influxdb",
    "mongodb",
    "mssql",
    "mysql",
    "neo4j",
    "postgresql",
    "redis",
    "sqlite",
    "yugabytedb",
}


def config_for(engine: str) -> ConnectionConfig:
    """Build the minimum valid configuration for an engine."""
    if engine == "sqlite":
        return ConnectionConfig(engine=engine, database=":memory:")
    if engine == "dynamodb":
        return ConnectionConfig(engine=engine, database="", host="us-east-1")
    if engine in {"redis", "cassandra", "elasticsearch"}:
        return ConnectionConfig(engine=engine, database="", host="localhost")
    return ConnectionConfig(
        engine=engine,
        host="localhost",
        database="query_analyzer",
        username="qa",
        password="qa-secret",
    )


@pytest.mark.contract
def test_registry_contains_exactly_the_supported_engines() -> None:
    """The public engine catalog must remain explicit and reviewable."""
    assert set(AdapterRegistry.list_engines()) == SUPPORTED_ENGINES


@pytest.mark.contract
@pytest.mark.parametrize("engine", sorted(SUPPORTED_ENGINES))
def test_every_supported_engine_implements_the_base_contract(engine: str) -> None:
    """Every registered engine must be constructible through the common factory."""
    adapter = AdapterRegistry.create(engine, config_for(engine))

    assert isinstance(adapter, BaseAdapter)
    assert adapter.is_connected() is False
    for method_name in (
        "connect",
        "disconnect",
        "test_connection",
        "execute_explain",
        "get_slow_queries",
        "get_metrics",
        "get_engine_info",
    ):
        method: Any = getattr(adapter, method_name)
        assert callable(method), f"{engine} does not implement {method_name}"


@pytest.mark.contract
@pytest.mark.parametrize("engine", sorted(SUPPORTED_ENGINES))
def test_every_supported_engine_rejects_an_invalid_port(engine: str) -> None:
    """Connection validation must be consistent before a driver is invoked."""
    if engine in {"sqlite", "dynamodb"}:
        pytest.skip(f"{engine} does not require a TCP port")

    with pytest.raises(ValueError, match="Puerto debe estar entre 1 y 65535"):
        ConnectionConfig(
            engine=engine,
            host="localhost",
            port=70000,
            database="" if engine in {"redis", "cassandra", "elasticsearch"} else "qa",
        )
