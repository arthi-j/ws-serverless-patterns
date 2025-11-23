# Serverless Users API

A secure, serverless REST API for user management built with AWS Lambda, API Gateway, DynamoDB, and Cognito authentication.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│                 │    │                  │    │                 │
│     Client      │───▶│   API Gateway    │───▶│ Lambda Authorizer│
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                │                        ▼
                                │               ┌─────────────────┐
                                │               │                 │
                                │               │  Cognito User   │
                                │               │      Pool       │
                                │               │                 │
                                │               └─────────────────┘
                                ▼
                       ┌─────────────────┐
                       │                 │
                       │ Users Lambda    │───────┐
                       │   Function      │       │
                       │                 │       │
                       └─────────────────┘       │
                                                 ▼
                                        ┌─────────────────┐
                                        │                 │
                                        │   DynamoDB      │
                                        │  Users Table    │
                                        │                 │
                                        └─────────────────┘
```

## Features

- **CRUD Operations**: Create, read, update, and delete users
- **JWT Authentication**: Secure API access using Cognito User Pool
- **Role-based Authorization**: Admin and user-level permissions
- **Serverless Architecture**: Auto-scaling and pay-per-use
- **Infrastructure as Code**: SAM template for deployment

## API Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/users` | List all users | Admin only |
| GET | `/users/{userid}` | Get user by ID | User/Admin |
| PUT | `/users` | Create new user | Admin only |
| PUT | `/users/{userid}` | Update user | User/Admin |
| DELETE | `/users/{userid}` | Delete user | User/Admin |

## Quick Start

### Prerequisites
- AWS CLI configured
- SAM CLI installed
- Python 3.10+

### Deploy
```bash
sam build
sam deploy --guided
```

### Authentication
```bash
# Get access token
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id <CLIENT_ID> \
  --auth-parameters USERNAME=<email>,PASSWORD=<password> \
  --query 'AuthenticationResult.AccessToken' \
  --output text
```

### Usage
```bash
# List users (admin only)
curl -H "Authorization: <ACCESS_TOKEN>" \
  https://<API_ID>.execute-api.<REGION>.amazonaws.com/Prod/users

# Get specific user
curl -H "Authorization: <ACCESS_TOKEN>" \
  https://<API_ID>.execute-api.<REGION>.amazonaws.com/Prod/users/<USER_ID>
```

## Project Structure

```
users/
├── src/api/
│   ├── users.py          # Main Lambda handler
│   └── authorizer.py     # JWT authorizer
├── events/               # Test events
├── tests/               # Unit & integration tests
├── template.yaml        # SAM template
└── requirements.txt     # Dependencies
```

## Security

- JWT token validation with Cognito
- Role-based access control
- CORS enabled
- Input validation required (see security findings)

## Development

### Local Testing
```bash
sam local start-api
```

### Run Tests
```bash
cd tests
pip install -r requirements.txt
pytest
```

## License

MIT-0 - See LICENSE file for details.