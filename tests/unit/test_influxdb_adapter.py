"""Tests for InfluxDB factual reports."""

from unittest.mock import MagicMock

from query_analyzer.adapters.models import ConnectionConfig
from query_analyzer.adapters.timeseries.influxdb import InfluxDBAdapter


def test_execute_explain_reports_flux_pipeline() -> None:
    adapter = InfluxDBAdapter(
        ConnectionConfig(
            engine="influxdb",
            host="localhost",
            database="bucket",
            password="token",
            extra={"org": "org"},
        )
    )
    adapter._is_connected = True
    adapter._org_id = "org"
    adapter._query_api = MagicMock()
    adapter._query_api.query_raw.return_value = MagicMock(data=b"#datatype,string\n,result\n,,42\n")

    report = adapter.execute_explain('from(bucket: "bucket") |> range(start: -1h) |> count()')

    assert report.engine == "influxdb"
    assert report.plan_summary
    assert report.raw_plan is not None
    assert "score" not in report.model_dump()
