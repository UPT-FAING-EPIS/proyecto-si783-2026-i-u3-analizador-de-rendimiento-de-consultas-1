"""Integration tests for connection diagnostics service using Docker."""

from query_analyzer.adapters.models import ConnectionConfig
from query_analyzer.core.connection_diagnostics import ConnectionDiagnosticsService


def test_postgresql_diagnostics_valid() -> None:
    """Verify diagnostics succeed for a valid PostgreSQL configuration."""
    config = ConnectionConfig(
        engine="postgresql",
        host="localhost",
        port=5432,
        database="query_analyzer",
        username="postgres",
        password="postgres123",
    )
    diagnostic = ConnectionDiagnosticsService.run_diagnostics("pg_valid", config)
    assert diagnostic.status == "connected"
    assert len(diagnostic.checks) == 4
    for check in diagnostic.checks:
        assert check.status == "success"


def test_postgresql_diagnostics_database_missing() -> None:
    """Verify database_missing classification for PostgreSQL."""
    config = ConnectionConfig(
        engine="postgresql",
        host="localhost",
        port=5432,
        database="non_existent_database_name_xyz",
        username="postgres",
        password="postgres123",
    )
    diagnostic = ConnectionDiagnosticsService.run_diagnostics("pg_db_missing", config)
    assert diagnostic.status == "database_missing"
    assert diagnostic.checks[0].status == "success"  # Config
    assert diagnostic.checks[1].status == "success"  # TCP
    assert diagnostic.checks[2].status == "failed"  # Connect
    assert diagnostic.checks[3].status == "skipped"  # Operatividad


def test_postgresql_diagnostics_authentication_failed() -> None:
    """Verify authentication_failed classification for PostgreSQL."""
    config = ConnectionConfig(
        engine="postgresql",
        host="localhost",
        port=5432,
        database="query_analyzer",
        username="postgres",
        password="wrong_password_abc_123",
    )
    diagnostic = ConnectionDiagnosticsService.run_diagnostics("pg_auth_failed", config)
    assert diagnostic.status == "authentication_failed"
    assert diagnostic.checks[0].status == "success"  # Config
    assert diagnostic.checks[1].status == "success"  # TCP
    assert diagnostic.checks[2].status == "failed"  # Connect
    assert diagnostic.checks[3].status == "skipped"  # Operatividad
    assert "wrong_password_abc_123" not in diagnostic.safe_message
    if diagnostic.technical_detail:
        assert "wrong_password_abc_123" not in diagnostic.technical_detail


def test_mysql_diagnostics_valid() -> None:
    """Verify diagnostics succeed for a valid MySQL configuration."""
    config = ConnectionConfig(
        engine="mysql",
        host="localhost",
        port=3306,
        database="query_analyzer",
        username="analyst",
        password="mysql123",
    )
    diagnostic = ConnectionDiagnosticsService.run_diagnostics("mysql_valid", config)
    assert diagnostic.status == "connected"
    assert len(diagnostic.checks) == 4
    for check in diagnostic.checks:
        assert check.status == "success"


def test_mysql_diagnostics_database_missing() -> None:
    """Verify database_missing classification for MySQL."""
    config = ConnectionConfig(
        engine="mysql",
        host="localhost",
        port=3306,
        database="non_existent_database_name_xyz",
        username="analyst",
        password="mysql123",
    )
    diagnostic = ConnectionDiagnosticsService.run_diagnostics("mysql_db_missing", config)
    assert diagnostic.status == "database_missing"
    assert diagnostic.checks[0].status == "success"  # Config
    assert diagnostic.checks[1].status == "success"  # TCP
    assert diagnostic.checks[2].status == "failed"  # Connect
    assert diagnostic.checks[3].status == "skipped"  # Operatividad


def test_mysql_diagnostics_authentication_failed() -> None:
    """Verify authentication_failed classification for MySQL."""
    config = ConnectionConfig(
        engine="mysql",
        host="localhost",
        port=3306,
        database="query_analyzer",
        username="analyst",
        password="wrong_password_abc_123",
    )
    diagnostic = ConnectionDiagnosticsService.run_diagnostics("mysql_auth_failed", config)
    assert diagnostic.status == "authentication_failed"
    assert diagnostic.checks[0].status == "success"  # Config
    assert diagnostic.checks[1].status == "success"  # TCP
    assert diagnostic.checks[2].status == "failed"  # Connect
    assert diagnostic.checks[3].status == "skipped"  # Operatividad
    assert "wrong_password_abc_123" not in diagnostic.safe_message
    if diagnostic.technical_detail:
        assert "wrong_password_abc_123" not in diagnostic.technical_detail
