"""DynamoDB integration tests using Moto as a local AWS emulator."""

import json

import boto3
import pytest
from moto import mock_aws

from query_analyzer.adapters.models import ConnectionConfig
from query_analyzer.adapters.nosql.dynamodb import DynamoDBAdapter


@pytest.mark.integration
def test_dynamodb_query_reports_consumed_capacity() -> None:
    """The adapter must execute a real boto3 Query against an emulated service."""
    with mock_aws():
        client = boto3.client("dynamodb", region_name="us-east-1")
        client.create_table(
            TableName="users",
            KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        client.put_item(TableName="users", Item={"pk": {"S": "user-1"}})

        adapter = DynamoDBAdapter(
            ConnectionConfig(engine="dynamodb", database="", host="us-east-1")
        )
        adapter.connect()
        try:
            report = adapter.execute_explain(
                json.dumps(
                    {
                        "TableName": "users",
                        "KeyConditionExpression": "pk = :pk",
                        "ExpressionAttributeValues": {":pk": {"S": "user-1"}},
                    }
                )
            )
        finally:
            adapter.disconnect()

    assert report.engine == "dynamodb"
    assert report.plan_summary == "Query on users"
    assert report.metrics["item_count"] == 1
    assert report.metrics["consumed_read_capacity"] >= 0
