"""Contracts for parsers that expose engine facts without deterministic judgments."""

import pytest

from query_analyzer.adapters.graph.neo4j_parser import Neo4jExplainParser
from query_analyzer.adapters.sql.cockroachdb_parser import CockroachDBParser
from query_analyzer.adapters.sql.mysql_parser import MySQLExplainParser
from query_analyzer.adapters.sql.postgresql_parser import PostgreSQLExplainParser
from query_analyzer.adapters.sql.sqlite_parser import SQLiteExplainParser
from query_analyzer.adapters.sql.yugabytedb_parser import YugabyteDBParser


@pytest.mark.parametrize(
    "parser",
    [
        PostgreSQLExplainParser(),
        MySQLExplainParser(),
        SQLiteExplainParser(),
        CockroachDBParser(),
        YugabyteDBParser(),
        Neo4jExplainParser(),
    ],
)
def test_parsers_expose_factual_contract_only(parser: object) -> None:
    assert hasattr(parser, "parse")
    assert hasattr(parser, "normalize_plan")
    assert not hasattr(parser, "identify_warnings")
    assert not hasattr(parser, "generate_recommendations")
    assert not hasattr(parser, "calculate_score")
    assert not hasattr(parser, "detect_anti_patterns_cypher")
