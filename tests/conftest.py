# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import pytest
import sys
import os
from unittest.mock import patch

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

@pytest.fixture(autouse=True)
def mock_aws_environment():
    """Mock AWS environment variables for all tests"""
    with patch.dict(os.environ, {
        'AWS_DEFAULT_REGION': 'us-east-1',
        'AWS_REGION': 'us-east-1',
        'AWS_XRAY_CONTEXT_MISSING': 'LOG_ERROR'
    }):
        yield

@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        'name': 'Test User',
        'email': 'test@example.com',
        'department': 'Engineering'
    }

@pytest.fixture
def api_gateway_event():
    """Base API Gateway event structure"""
    return {
        'httpMethod': 'GET',
        'resource': '/users',
        'pathParameters': None,
        'body': None,
        'headers': {
            'Content-Type': 'application/json'
        },
        'requestContext': {
            'requestId': 'test-request-id'
        }
    }