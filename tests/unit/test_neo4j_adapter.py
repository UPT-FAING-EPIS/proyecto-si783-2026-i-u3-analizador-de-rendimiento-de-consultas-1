"""Tests for Neo4j factual reports."""

from query_analyzer.adapters.graph.neo4j import Neo4jAdapter
from query_analyzer.adapters.models import ConnectionConfig


def test_build_plan_tree_preserves_profile_values() -> None:
    adapter = Neo4jAdapter(
        ConnectionConfig(
            engine="neo4j",
            host="localhost",
            database="neo4j",
            username="neo4j",
            password="pass",
        )
    )
    plan = adapter._build_plan_tree_from_neo4j(
        {
            "operatorType": "ProduceResults",
            "rows": 2,
            "dbHits": 1,
            "children": [{"operatorType": "NodeIndexSeek", "rows": 2, "dbHits": 3}],
        }
    )
    assert plan is not None
    assert plan.node_type == "ProduceResults"
    assert plan.children[0].node_type == "NodeIndexSeek"


def test_plan_summary_is_factual() -> None:
    adapter = Neo4jAdapter(
        ConnectionConfig(
            engine="neo4j",
            host="localhost",
            database="neo4j",
            username="neo4j",
            password="pass",
        )
    )
    assert adapter._summarize_plan({"operatorType": "NodeIndexSeek", "rows": 4}) == (
        "NodeIndexSeek (4 rows)"
    )
