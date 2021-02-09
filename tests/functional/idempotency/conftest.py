import datetime
import hashlib
import json
import os

import pytest
from botocore import stub
from botocore.config import Config

from aws_lambda_powertools.utilities.idempotency import DynamoDBPersistenceLayer

TABLE_NAME = "TEST_TABLE"


@pytest.fixture(scope="module")
def config() -> Config:
    return Config(region_name="us-east-1")


@pytest.fixture(scope="module")
def lambda_apigw_event():
    full_file_name = os.path.dirname(os.path.realpath(__file__)) + "/../../events/" + "apiGatewayProxyV2Event.json"
    with open(full_file_name) as fp:
        event = json.load(fp)

    return event


@pytest.fixture
def timestamp_future():
    return str(int((datetime.datetime.now() + datetime.timedelta(seconds=3600)).timestamp()))


@pytest.fixture
def timestamp_expired():
    now = datetime.datetime.now()
    period = datetime.timedelta(seconds=6400)
    return str(int((now - period).timestamp()))


@pytest.fixture(scope="module")
def lambda_response():
    return {"message": "test", "statusCode": 200}


@pytest.fixture
def expected_params_update_item(lambda_response, hashed_idempotency_key):
    return {
        "ExpressionAttributeNames": {"#expiry": "expiration", "#response_data": "data", "#status": "status"},
        "ExpressionAttributeValues": {
            ":expiry": stub.ANY,
            ":response_data": json.dumps(lambda_response),
            ":status": "COMPLETED",
        },
        "Key": {"id": hashed_idempotency_key},
        "TableName": "TEST_TABLE",
        "UpdateExpression": "SET #response_data = :response_data, " "#expiry = :expiry, #status = :status",
    }


@pytest.fixture
def expected_params_update_item_with_validation(lambda_response, hashed_idempotency_key, hashed_validation_key):
    return {
        "ExpressionAttributeNames": {
            "#expiry": "expiration",
            "#response_data": "data",
            "#status": "status",
            "#validation_key": "validation",
        },
        "ExpressionAttributeValues": {
            ":expiry": stub.ANY,
            ":response_data": json.dumps(lambda_response),
            ":status": "COMPLETED",
            ":validation_key": hashed_validation_key,
        },
        "Key": {"id": hashed_idempotency_key},
        "TableName": "TEST_TABLE",
        "UpdateExpression": "SET #response_data = :response_data, "
        "#expiry = :expiry, #status = :status, "
        "#validation_key = :validation_key",
    }


@pytest.fixture
def expected_params_put_item(hashed_idempotency_key):
    return {
        "ConditionExpression": "attribute_not_exists(id) OR expiration < :now",
        "ExpressionAttributeValues": {":now": stub.ANY},
        "Item": {"expiration": stub.ANY, "id": hashed_idempotency_key, "status": "INPROGRESS"},
        "TableName": "TEST_TABLE",
    }


@pytest.fixture
def expected_params_put_item_with_validation(hashed_idempotency_key, hashed_validation_key):
    return {
        "ConditionExpression": "attribute_not_exists(id) OR expiration < :now",
        "ExpressionAttributeValues": {":now": stub.ANY},
        "Item": {
            "expiration": stub.ANY,
            "id": hashed_idempotency_key,
            "status": "INPROGRESS",
            "validation": hashed_validation_key,
        },
        "TableName": "TEST_TABLE",
    }


@pytest.fixture
def hashed_idempotency_key(lambda_apigw_event):
    return hashlib.md5(json.dumps(lambda_apigw_event["body"]).encode()).hexdigest()


@pytest.fixture
def hashed_validation_key(lambda_apigw_event):
    return hashlib.md5(json.dumps(lambda_apigw_event["requestContext"]).encode()).hexdigest()


@pytest.fixture
def persistence_store(config, request):
    persistence_store = DynamoDBPersistenceLayer(
        event_key_jmespath="body",
        table_name=TABLE_NAME,
        boto_config=config,
        use_local_cache=request.param["use_local_cache"],
    )
    return persistence_store


@pytest.fixture
def persistence_store_with_validation(config, request):
    persistence_store = DynamoDBPersistenceLayer(
        event_key_jmespath="body",
        table_name=TABLE_NAME,
        boto_config=config,
        use_local_cache=request.param,
        payload_validation_jmespath="requestContext",
    )
    return persistence_store
