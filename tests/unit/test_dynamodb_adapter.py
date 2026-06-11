"""Tests for DynamoDB factual execution reports."""

import json
from unittest.mock import MagicMock

from query_analyzer.adapters.models import ConnectionConfig
from query_analyzer.adapters.nosql.dynamodb import DynamoDBAdapter
from query_analyzer.adapters.nosql.dynamodb_parser import DynamoDBParser


def test_parser_extracts_operation_and_table() -> None:
    parser = DynamoDBParser()
    payload = parser.parse_query_string(
        json.dumps(
            {
                "TableName": "users",
                "KeyConditionExpression": "pk = :pk",
            }
        )
    )
    assert parser.extract_operation_type(payload) == "Query"
    assert parser.extract_table_name(payload) == "users"


def test_execute_explain_returns_capacity_metrics() -> None:
    adapter = DynamoDBAdapter(ConnectionConfig(engine="dynamodb", database="", host="us-east-1"))
    adapter._is_connected = True
    adapter._parser = DynamoDBParser()

    class ResourceNotFoundException(Exception):  # noqa: N818 - mirrors boto3 API name
        pass

    class ValidationException(Exception):  # noqa: N818 - mirrors boto3 API name
        pass

    adapter._dynamodb_client = MagicMock()
    adapter._dynamodb_client.exceptions.ResourceNotFoundException = ResourceNotFoundException
    adapter._dynamodb_client.exceptions.ValidationException = ValidationException
    adapter._dynamodb_client.query.return_value = {
        "Count": 2,
        "ScannedCount": 3,
        "ConsumedCapacity": {"CapacityUnits": 1.5},
    }

    report = adapter.execute_explain(
        json.dumps(
            {
                "TableName": "users",
                "KeyConditionExpression": "pk = :pk",
            }
        )
    )

    assert report.plan_summary == "Query on users"
    assert report.metrics["item_count"] == 2
    assert report.metrics["scanned_count"] == 3
    assert "score" not in report.model_dump()
