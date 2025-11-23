# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import os
import boto3
import uuid
import pytest
from moto import mock_dynamodb
from contextlib import contextmanager
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError

USERS_MOCK_TABLE_NAME = 'Users'
UUID_MOCK_VALUE_JOHN = 'f8216640-91a2-11eb-8ab9-57aa454facef'
UUID_MOCK_VALUE_JANE = '31a9f940-917b-11eb-9054-67837e2c40b0'
UUID_MOCK_VALUE_NEW_USER = 'new-user-guid'


def mock_uuid():
    return UUID_MOCK_VALUE_NEW_USER


@contextmanager
def my_test_environment():
    with mock_dynamodb():
        set_up_dynamodb()
        put_data_dynamodb()
        yield

def set_up_dynamodb():
    conn = boto3.client('dynamodb')
    conn.create_table(
        TableName=USERS_MOCK_TABLE_NAME,
        KeySchema=[{'AttributeName': 'userid', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'userid', 'AttributeType': 'S'}],
        ProvisionedThroughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1}
    )

def put_data_dynamodb():
    conn = boto3.client('dynamodb')
    conn.put_item(
        TableName=USERS_MOCK_TABLE_NAME,
        Item={
            'userid': {'S': UUID_MOCK_VALUE_JOHN},
            'name': {'S': 'John Doe'},
            'timestamp': {'S': '2021-03-30T21:57:49.860Z'}
        }
    )
    conn.put_item(
        TableName=USERS_MOCK_TABLE_NAME,
        Item={
            'userid': {'S': UUID_MOCK_VALUE_JANE},
            'name': {'S': 'Jane Doe'},
            'timestamp': {'S': '2021-03-30T17:13:06.516Z'}
        }
    )

@patch.dict(os.environ, {'USERS_TABLE': USERS_MOCK_TABLE_NAME, 'AWS_XRAY_CONTEXT_MISSING': 'LOG_ERROR'})
def test_get_list_of_users():
    with my_test_environment():
        from src.api import users
        with open('./events/event-get-all-users.json', 'r') as f:
            apigw_get_all_users_event = json.load(f)
        expected_response = [
            {
                'userid': UUID_MOCK_VALUE_JOHN,
                'name': 'John Doe',
                'timestamp': '2021-03-30T21:57:49.860Z'
            },
            {
                'userid': UUID_MOCK_VALUE_JANE,
                'name': 'Jane Doe',
                'timestamp': '2021-03-30T17:13:06.516Z'
            }
        ]
        ret = users.lambda_handler(apigw_get_all_users_event, '')
        assert ret['statusCode'] == 200
        data = json.loads(ret['body'])
        assert data == expected_response

def test_get_single_user():
    with my_test_environment():
        from src.api import users
        with open('./events/event-get-user-by-id.json', 'r') as f:
            apigw_event = json.load(f)
        expected_response = {
            'userid': UUID_MOCK_VALUE_JOHN,
            'name': 'John Doe',
            'timestamp': '2021-03-30T21:57:49.860Z'
        }
        ret = users.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        data = json.loads(ret['body'])
        assert data == expected_response

def test_get_single_user_wrong_id():
    with my_test_environment():
        from src.api import users
        with open('./events/event-get-user-by-id.json', 'r') as f:
            apigw_event = json.load(f)
            apigw_event['pathParameters']['userid'] = '123456789'
            apigw_event['rawPath'] = '/users/123456789'
        ret = users.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        assert json.loads(ret['body']) == {}

@patch('uuid.uuid1', mock_uuid)
@pytest.mark.freeze_time('2001-01-01')
def test_add_user():
    with my_test_environment():
        from src.api import users
        with open('./events/event-put-user.json', 'r') as f:
            apigw_event = json.load(f)
        expected_response = json.loads(apigw_event['body'])
        ret = users.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        data = json.loads(ret['body'])
        assert data['userid'] == UUID_MOCK_VALUE_NEW_USER
        assert data['timestamp'] == '2001-01-01T00:00:00'
        assert data['name'] == expected_response['name']

@pytest.mark.freeze_time('2001-01-01')
def test_add_user_with_id():
    with my_test_environment():
        from src.api import users
        with open('./events/event-put-user.json', 'r') as f:
            apigw_event = json.load(f)
        expected_response = json.loads(apigw_event['body'])
        apigw_event['body'] = apigw_event['body'].replace('}', ', \"userid\":\"123456789\"}')
        ret = users.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        data = json.loads(ret['body'])
        assert data['userid'] == '123456789'
        assert data['timestamp'] == '2001-01-01T00:00:00'
        assert data['name'] == expected_response['name']

def test_delete_user():
    with my_test_environment():
        from src.api import users
        with open('./events/event-delete-user-by-id.json', 'r') as f:
            apigw_event = json.load(f)
        ret = users.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        assert json.loads(ret['body']) == {}

# Error handling tests
@patch.dict(os.environ, {'USERS_TABLE': USERS_MOCK_TABLE_NAME})
def test_unsupported_route():
    with my_test_environment():
        from src.api import users
        event = {
            'httpMethod': 'POST',
            'resource': '/unsupported',
            'pathParameters': None,
            'body': None
        }
        ret = users.lambda_handler(event, '')
        assert ret['statusCode'] == 400
        data = json.loads(ret['body'])
        assert data['Message'] == 'Unsupported route'

@patch.dict(os.environ, {'USERS_TABLE': USERS_MOCK_TABLE_NAME})
def test_missing_path_parameters():
    with my_test_environment():
        from src.api import users
        event = {
            'httpMethod': 'GET',
            'resource': '/users/{userid}',
            'pathParameters': None
        }
        ret = users.lambda_handler(event, '')
        assert ret['statusCode'] == 400
        data = json.loads(ret['body'])
        assert 'Error:' in data

@patch.dict(os.environ, {'USERS_TABLE': USERS_MOCK_TABLE_NAME})
def test_invalid_json_body():
    with my_test_environment():
        from src.api import users
        event = {
            'httpMethod': 'PUT',
            'resource': '/users',
            'body': 'invalid json'
        }
        ret = users.lambda_handler(event, '')
        assert ret['statusCode'] == 400
        data = json.loads(ret['body'])
        assert 'Error:' in data

@patch.dict(os.environ, {'USERS_TABLE': USERS_MOCK_TABLE_NAME})
def test_missing_body():
    with my_test_environment():
        from src.api import users
        event = {
            'httpMethod': 'PUT',
            'resource': '/users',
            'body': None
        }
        ret = users.lambda_handler(event, '')
        assert ret['statusCode'] == 400
        data = json.loads(ret['body'])
        assert 'Error:' in data

@patch.dict(os.environ, {'USERS_TABLE': USERS_MOCK_TABLE_NAME})
def test_dynamodb_error():
    with mock_dynamodb():
        from src.api import users
        # Don't set up DynamoDB table to trigger error
        event = {
            'httpMethod': 'GET',
            'resource': '/users'
        }
        ret = users.lambda_handler(event, '')
        assert ret['statusCode'] == 400
        data = json.loads(ret['body'])
        assert 'Error:' in data

@patch.dict(os.environ, {'USERS_TABLE': USERS_MOCK_TABLE_NAME})
@pytest.mark.freeze_time('2001-01-01')
def test_update_user_by_id():
    with my_test_environment():
        from src.api import users
        event = {
            'httpMethod': 'PUT',
            'resource': '/users/{userid}',
            'pathParameters': {'userid': 'test-user-id'},
            'body': json.dumps({'name': 'Updated User', 'email': 'updated@test.com'})
        }
        ret = users.lambda_handler(event, '')
        assert ret['statusCode'] == 200
        data = json.loads(ret['body'])
        assert data['userid'] == 'test-user-id'
        assert data['name'] == 'Updated User'
        assert data['email'] == 'updated@test.com'
        assert data['timestamp'] == '2001-01-01T00:00:00'

@patch.dict(os.environ, {'USERS_TABLE': USERS_MOCK_TABLE_NAME})
def test_response_headers():
    with my_test_environment():
        from src.api import users
        event = {
            'httpMethod': 'GET',
            'resource': '/users'
        }
        ret = users.lambda_handler(event, '')
        assert ret['headers']['Content-Type'] == 'application/json'
        assert ret['headers']['Access-Control-Allow-Origin'] == '*'

@patch.dict(os.environ, {'USERS_TABLE': USERS_MOCK_TABLE_NAME})
def test_empty_scan_result():
    with mock_dynamodb():
        set_up_dynamodb()  # Empty table
        from src.api import users
        event = {
            'httpMethod': 'GET',
            'resource': '/users'
        }
        ret = users.lambda_handler(event, '')
        assert ret['statusCode'] == 200
        data = json.loads(ret['body'])
        assert data == []

