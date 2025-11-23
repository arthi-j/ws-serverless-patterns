# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import os
import pytest
from unittest.mock import patch, MagicMock
from moto import mock_dynamodb
from contextlib import contextmanager

USERS_MOCK_TABLE_NAME = 'Users'

@contextmanager
def test_environment():
    with mock_dynamodb():
        import boto3
        conn = boto3.client('dynamodb')
        conn.create_table(
            TableName=USERS_MOCK_TABLE_NAME,
            KeySchema=[{'AttributeName': 'userid', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'userid', 'AttributeType': 'S'}],
            ProvisionedThroughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1}
        )
        yield

class TestInputValidation:
    """Test input validation and sanitization"""
    
    @patch.dict(os.environ, {'USERS_TABLE': USERS_MOCK_TABLE_NAME})
    def test_sql_injection_attempt_in_userid(self):
        with test_environment():
            from src.api import users
            event = {
                'httpMethod': 'GET',
                'resource': '/users/{userid}',
                'pathParameters': {'userid': "'; DROP TABLE users; --"}
            }
            ret = users.lambda_handler(event, '')
            assert ret['statusCode'] == 200  # Should handle gracefully
    
    @patch.dict(os.environ, {'USERS_TABLE': USERS_MOCK_TABLE_NAME})
    def test_mass_assignment_vulnerability(self):
        with test_environment():
            from src.api import users
            malicious_payload = {
                'name': 'Test User',
                'email': 'test@example.com',
                'admin': True,  # Malicious field
                'role': 'administrator',  # Another malicious field
                'internal_flag': 'sensitive_data'
            }
            event = {
                'httpMethod': 'PUT',
                'resource': '/users',
                'body': json.dumps(malicious_payload)
            }
            ret = users.lambda_handler(event, '')
            assert ret['statusCode'] == 200
            data = json.loads(ret['body'])
            # Currently vulnerable - all fields are accepted
            assert 'admin' in data
            assert 'role' in data

class TestErrorHandling:
    """Test error handling scenarios"""
    
    #@patch.dict(os.environ, {'USERS_TABLE': USERS_MOCK_TABLE_NAME})
    def test_missing_environment_variable(self):
        with test_environment():
            from src.api import users
            event = {
                'httpMethod': 'GET',
                'resource': '/users'
            }
            ret = users.lambda_handler(event, '')
            assert ret['statusCode'] == 400
    
    @patch.dict(os.environ, {'USERS_TABLE': USERS_MOCK_TABLE_NAME})
    def test_malformed_path_parameters(self):
        with test_environment():
            from src.api import users
            event = {
                'httpMethod': 'GET',
                'resource': '/users/{userid}',
                'pathParameters': {'wrong_key': 'value'}
            }
            ret = users.lambda_handler(event, '')
            assert ret['statusCode'] == 400
    
    @patch.dict(os.environ, {'USERS_TABLE': 'DOES_NOT_EXIST'})
    def test_empty_body_handling(self):
        with test_environment():
            from src.api import users
            event = {
                'httpMethod': 'PUT',
                'resource': '/users',
                'body': ''
            }
            ret = users.lambda_handler(event, '')
            assert ret['statusCode'] == 400

class TestDataSanitization:
    """Test data sanitization and validation"""
    
    @patch.dict(os.environ, {'USERS_TABLE': USERS_MOCK_TABLE_NAME})
    def test_xss_payload_in_user_data(self):
        with test_environment():
            from src.api import users
            xss_payload = {
                'name': '<script>alert("xss")</script>',
                'email': 'test@example.com'
            }
            event = {
                'httpMethod': 'PUT',
                'resource': '/users',
                'body': json.dumps(xss_payload)
            }
            ret = users.lambda_handler(event, '')
            assert ret['statusCode'] == 200
            data = json.loads(ret['body'])
            # Currently no sanitization - potential XSS
            assert '<script>' in data['name']
    
    @patch.dict(os.environ, {'USERS_TABLE': USERS_MOCK_TABLE_NAME})
    def test_oversized_payload(self):
        with test_environment():
            from src.api import users
            large_payload = {
                'name': 'A' * 10000,  # Very large name
                'description': 'B' * 50000  # Very large description
            }
            event = {
                'httpMethod': 'PUT',
                'resource': '/users',
                'body': json.dumps(large_payload)
            }
            ret = users.lambda_handler(event, '')
            # Should handle large payloads gracefully
            assert ret['statusCode'] in [200, 400]

class TestAuthorizationBypass:
    """Test potential authorization bypass scenarios"""
    
    @patch.dict(os.environ, {'USERS_TABLE': USERS_MOCK_TABLE_NAME})
    def test_userid_manipulation(self):
        with test_environment():
            from src.api import users
            # Attempt to access another user's data
            event = {
                'httpMethod': 'GET',
                'resource': '/users/{userid}',
                'pathParameters': {'userid': '../admin'}
            }
            ret = users.lambda_handler(event, '')
            assert ret['statusCode'] == 200  # Should validate userid format
    
    @patch.dict(os.environ, {'USERS_TABLE': USERS_MOCK_TABLE_NAME})
    def test_path_traversal_attempt(self):
        with test_environment():
            from src.api import users
            event = {
                'httpMethod': 'GET',
                'resource': '/users/{userid}',
                'pathParameters': {'userid': '../../etc/passwd'}
            }
            ret = users.lambda_handler(event, '')
            assert ret['statusCode'] == 200  # Should handle gracefully