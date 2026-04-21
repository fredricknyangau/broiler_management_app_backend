# API Documentation Guide

## Quick Links

- **Interactive API Docs (Swagger UI):** http://localhost:8080/api/v1/docs
- **Alternative API Docs (ReDoc):** http://localhost:8080/api/v1/redoc
- **OpenAPI Schema (JSON):** http://localhost:8080/api/v1/openapi.json

## Running the Development Server

```bash
cd backend
poetry install
poetry run uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8080`

## API Endpoints Overview

### Authentication (`/auth`)
- `POST /auth/login` - User login with email/password
- `POST /auth/register` - Register new user account
- `POST /auth/send-otp` - Send OTP verification code
- `POST /auth/verify-otp` - Verify OTP and complete registration
- `POST /auth/google` - Google SSO authentication
- `POST /auth/apple` - Apple SSO authentication
- `GET /auth/me` - Get current user profile

### Flocks/Batches (`/flocks`)
- `GET /flocks` - List all flocks
- `GET /flocks/{id}` - Get flock details
- `POST /flocks` - Create new flock
- `PATCH /flocks/{id}` - Update flock
- `DELETE /flocks/{id}` - Archive flock

### Farms (`/farms`)
- `GET /farms` - List farms
- `POST /farms` - Create farm
- `PATCH /farms/{id}` - Update farm
- `DELETE /farms/{id}` - Delete farm

### Events (`/events`)
- `GET /events/mortality` - List mortality events
- `POST /events/mortality` - Record mortality
- `GET /events/feed` - List feed consumption events
- `POST /events/feed` - Record feed consumption
- `GET /events/vaccination` - List vaccinations
- `POST /events/vaccination` - Record vaccination
- `GET /events/weight` - List weight records
- `POST /events/weight` - Record weight

### Finance (`/finance`)
- `GET /finance/expenditures` - List expenses
- `POST /finance/expenditures` - Record expense
- `GET /finance/sales` - List sales
- `POST /finance/sales` - Record sale
- `DELETE /finance/expenditures/{id}` - Delete expense
- `DELETE /finance/sales/{id}` - Delete sale

### AI Advisory (`/ai`)
- `POST /ai/feed-recommendation` - Get feed recommendations
- `POST /ai/mortality-analysis` - Analyze mortality patterns
- `POST /ai/disease-risk` - Assess disease risk
- `POST /ai/harvest-prediction` - Predict harvest metrics
- `POST /ai/chat` - AI chat advisory
- `POST /ai/voice-record` - Process voice observations

### Analytics (`/analytics`)
- `GET /analytics/dashboard-metrics` - Dashboard KPIs
- `GET /analytics/charts/revenue-vs-expenses` - Financial charts
- `GET /analytics/benchmarks` - Industry benchmarks

### Billing (`/billing`)
- `GET /billing/plans` - List subscription plans
- `GET /billing/my-subscription` - Get user subscription
- `POST /billing/subscribe` - Subscribe to plan
- `POST /billing/mpesa/callback` - M-Pesa payment callback

### Community (`/community`)
- `GET /community/categories` - List post categories
- `GET /community/feed` - Get community feed
- `POST /community/posts` - Create post
- `POST /community/posts/{id}/comments` - Add comment
- `POST /community/posts/{id}/like` - Like post

### Admin (`/admin`)
- `GET /admin/users` - List all users
- `POST /admin/users` - Create user
- `DELETE /admin/users/{id}` - Delete user
- `GET /admin/audit-logs` - View audit logs

## Authentication

### Bearer Token Example

```bash
curl -X GET http://localhost:8080/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Login Example

```bash
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "farmer@example.com",
    "password": "secure_password"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

## Response Formats

### Success Response
```json
{
  "status": "success",
  "data": { /* resource data */ },
  "message": "Operation completed successfully"
}
```

### Error Response
```json
{
  "status": "error",
  "error": "validation_error",
  "message": "Invalid input",
  "details": [
    {
      "field": "email",
      "message": "Invalid email format"
    }
  ]
}
```

## Rate Limiting

- **Standard:** 1000 requests per hour per user
- **Premium:** 5000 requests per hour per user

Rate limit headers:
- `X-RateLimit-Limit`: Total requests allowed
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Unix timestamp of next reset

## Error Codes

| Code | Status | Description |
|------|--------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created |
| 400 | Bad Request | Invalid input |
| 401 | Unauthorized | Missing/invalid auth token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Resource already exists |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Server Error | Internal server error |
| 503 | Service Unavailable | Server temporarily unavailable |

## Testing

### Run All Tests
```bash
cd backend
poetry run pytest tests/ -v
```

### Run Specific Test
```bash
poetry run pytest tests/test_main.py::test_root_endpoint -v
```

### Generate Coverage Report
```bash
poetry run pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html
```

## Generating Client SDKs

The OpenAPI schema can be used to automatically generate client SDKs:

### Generate Python Client
```bash
pip install openapi-generator-cli
openapi-generator-cli generate \
  -i http://localhost:8080/api/v1/openapi.json \
  -g python \
  -o ./generated_python_client
```

### Generate TypeScript Client
```bash
openapi-generator-cli generate \
  -i http://localhost:8080/api/v1/openapi.json \
  -g typescript-axios \
  -o ./generated_ts_client
```

## Webhook Events

Subscribe to events via webhooks:

```bash
curl -X POST http://localhost:8080/api/v1/webhooks \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "flock.mortality_recorded",
    "url": "https://your-domain.com/webhook",
    "active": true
  }'
```

Supported events:
- `flock.created`
- `flock.updated`
- `mortality.recorded`
- `sale.completed`
- `subscription.activated`
- `alert.triggered`

## Deprecation Policy

API versions will be maintained for **12 months** after deprecation notice:

1. Announce deprecation in release notes
2. Mark endpoints with `deprecated: true` in OpenAPI
3. Support for 12 months
4. Remove in major version release

## Support & Issues

- **Documentation:** [GitHub Wiki](https://github.com/kukufiti/backend/wiki)
- **Issues:** [GitHub Issues](https://github.com/kukufiti/backend/issues)
- **Email:** api-support@kukufiti.app

