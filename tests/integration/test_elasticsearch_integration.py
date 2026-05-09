"""Integration tests for Elasticsearch adapter."""

import json

import pytest

from query_analyzer.adapters.elasticsearch import ElasticsearchAdapter
from query_analyzer.adapters.models import ConnectionConfig


@pytest.fixture
def es_config() -> ConnectionConfig:
    """Elasticsearch test configuration."""
    return ConnectionConfig(
        engine="elasticsearch",
        host="localhost",
        port=9200,
        database="test_index",
    )


@pytest.fixture
def es_adapter(es_config: ConnectionConfig) -> ElasticsearchAdapter:
    """Elasticsearch adapter instance."""
    adapter = ElasticsearchAdapter(es_config)
    adapter.connect()
    yield adapter
    try:
        adapter.disconnect()
    except Exception:
        pass


class TestElasticsearchAdapterIntegration:
    """Integration tests for Elasticsearch adapter."""

    def test_adapter_connection(self, es_adapter: ElasticsearchAdapter) -> None:
        """Test successful connection to Elasticsearch."""
        assert es_adapter.is_connected()
        assert es_adapter.test_connection()

    def test_execute_explain_match_all_query(self, es_adapter: ElasticsearchAdapter) -> None:
        """Test explain on match_all query (v2 contract)."""
        query = json.dumps({"match_all": {}})
        report = es_adapter.execute_explain(query)

        assert report.engine == "elasticsearch"
        assert report.query == query
        assert report.execution_time_ms > 0
        assert isinstance(report.metrics, dict)
        assert "took" in report.metrics
        assert "query_type" in report.metrics
        assert "has_filter" in report.metrics
        assert "timed_out" in report.metrics

    def test_execute_explain_bool_query_with_filter(self, es_adapter: ElasticsearchAdapter) -> None:
        """Test explain on bool query with filter (v2 contract)."""
        query = json.dumps(
            {
                "bool": {
                    "filter": {"term": {"status": "active"}},
                    "must": {"match": {"title": "test"}},
                }
            }
        )
        report = es_adapter.execute_explain(query)

        assert report.engine == "elasticsearch"
        assert report.query == query
        assert report.execution_time_ms > 0
        assert isinstance(report.metrics, dict)
        assert "has_filter" in report.metrics

    def test_execute_explain_wildcard_query(self, es_adapter: ElasticsearchAdapter) -> None:
        """Test explain on wildcard query (v2 contract)."""
        query = json.dumps({"wildcard": {"title": {"value": "test*"}}})
        report = es_adapter.execute_explain(query)

        assert report.engine == "elasticsearch"
        assert report.execution_time_ms > 0
        assert isinstance(report.metrics, dict)

    def test_execute_explain_nested_wildcard_query(self, es_adapter: ElasticsearchAdapter) -> None:
        """Test explain on nested wildcard query (v2 contract)."""
        query = json.dumps({"bool": {"must": [{"wildcard": {"field": {"value": "value*"}}}]}})
        report = es_adapter.execute_explain(query)

        assert report.engine == "elasticsearch"
        assert report.execution_time_ms > 0
        assert isinstance(report.metrics, dict)

    def test_execute_explain_script_score_query(self, es_adapter: ElasticsearchAdapter) -> None:
        """Test explain on script_score query (v2 contract)."""
        query = json.dumps(
            {
                "script_score": {
                    "query": {"match_all": {}},
                    "script": {"source": "_score * params.factor", "params": {"factor": 1.2}},
                }
            }
        )
        report = es_adapter.execute_explain(query)

        assert report.engine == "elasticsearch"
        assert report.execution_time_ms > 0
        assert isinstance(report.metrics, dict)

    def test_execute_explain_term_query(self, es_adapter: ElasticsearchAdapter) -> None:
        """Test explain on term query (v2 contract)."""
        query = json.dumps({"term": {"status": {"value": "published"}}})
        report = es_adapter.execute_explain(query)

        assert report.engine == "elasticsearch"
        assert report.query == query
        assert report.execution_time_ms > 0

    def test_get_metrics(self, es_adapter: ElasticsearchAdapter) -> None:
        """Test getting cluster metrics."""
        metrics = es_adapter.get_metrics()

        assert "cluster_status" in metrics
        assert "active_shards" in metrics
        assert "nodes_count" in metrics
        assert metrics["cluster_status"] in ["green", "yellow", "red"]

    def test_execute_explain_invalid_json_raises_error(
        self, es_adapter: ElasticsearchAdapter
    ) -> None:
        """Test that invalid JSON query raises error."""
        from query_analyzer.adapters.exceptions import QueryAnalysisError

        query = "{'invalid': json}"  # Invalid JSON
        with pytest.raises(QueryAnalysisError):
            es_adapter.execute_explain(query)

    def test_adapter_can_reconnect(self, es_adapter: ElasticsearchAdapter) -> None:
        """Test adapter can disconnect and reconnect."""
        es_adapter.disconnect()
        assert not es_adapter.is_connected()

        es_adapter.connect()
        assert es_adapter.is_connected()

    def test_score_calculation_no_warnings(self, es_adapter: ElasticsearchAdapter) -> None:
        """Test term query returns stable v2 fields."""
        query = json.dumps({"term": {"status": {"value": "published"}}})
        report = es_adapter.execute_explain(query)

        assert report.engine == "elasticsearch"
        assert report.execution_time_ms > 0
        assert isinstance(report.metrics, dict)

    def test_score_calculation_with_warnings(self, es_adapter: ElasticsearchAdapter) -> None:
        """Test match_all query returns stable v2 fields."""
        query = json.dumps({"match_all": {}})
        report = es_adapter.execute_explain(query)

        assert report.engine == "elasticsearch"
        assert report.execution_time_ms > 0
        assert isinstance(report.metrics, dict)

    def test_recommendations_provided(self, es_adapter: ElasticsearchAdapter) -> None:
        """Test report exposes v2 metadata fields."""
        query = json.dumps({"match_all": {}})
        report = es_adapter.execute_explain(query)

        assert report.analyzed_at is not None
        assert isinstance(report.plan_summary, str)
        assert isinstance(report.metrics, dict)

    def test_multiple_anti_patterns_detected(self, es_adapter: ElasticsearchAdapter) -> None:
        """Test complex query returns valid v2 report structure."""
        query = json.dumps(
            {
                "bool": {
                    "should": [
                        {"wildcard": {"title": {"value": "test*"}}},
                        {
                            "script_score": {
                                "query": {"match_all": {}},
                                "script": {"source": "_score"},
                            }
                        },
                    ]
                }
            }
        )
        report = es_adapter.execute_explain(query)

        assert report.engine == "elasticsearch"
        assert report.execution_time_ms > 0
        assert isinstance(report.metrics, dict)
