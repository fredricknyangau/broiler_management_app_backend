# Backend - Environment Setup

## Quick Start

```bash
# Create local environment file
cp .env.example .env.local

# Edit with your values
nano .env.local

# Run (automatically loads .env.local)
python -m uvicorn app.main:app --reload
```

## Critical Variables for Google Sign-In

```env
# MUST match the Web Client ID from Google Cloud Console
# Same value as in mobile app .env.local
GOOGLE_CLIENT_ID=227712759483-p0dtbdvjrtji59mhlet9kvprgm552gbh.apps.googleusercontent.com

# Secret key for JWT (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
SECRET_KEY=your-super-secret-key-change-this-in-production
```

## Database & Redis Setup

```env
# Local PostgreSQL
DATABASE_URL=postgresql+asyncpg://broiler_user:broiler_pass@localhost:5432/broiler_farm_db

# Local Redis (for OTP caching)
REDIS_URL=redis://localhost:6379/0
```

## SMS Configuration (Africa's Talking)

```env
AFRICASTALKING_USERNAME=sandbox
AFRICASTALKING_API_KEY=your_api_key
```

## Running Backend

```bash
# Development (loads .env.local automatically)
python -m uvicorn app.main:app --reload

# Or with poetry
poetry run uvicorn app.main:app --reload

# With Docker Compose
docker-compose up
```

## Production Environment Variables

For Render or other cloud deployment:

```
GOOGLE_CLIENT_ID=227712759483-p0dtbdvjrtji59mhlet9kvprgm552gbh.apps.googleusercontent.com
DATABASE_URL=postgresql+asyncpg://user:pass@host/db
REDIS_URL=redis://:password@host:port/0
SECRET_KEY=***strong-random-key***
DEBUG=False
```

## Important Notes

- **Never commit `.env` files** — Only `.env.example` is in version control
- **SECRET_KEY must be changed in production** — Generate a new one
- **GOOGLE_CLIENT_ID must match mobile app** — Both should use Web Client ID
- Backend must have `GOOGLE_CLIENT_ID` set for `/auth/google` endpoint to work

## Troubleshooting

### "Google SSO is not configured"
Backend's `GOOGLE_CLIENT_ID` environment variable is not set

### "Invalid Google ID token"
1. Verify `GOOGLE_CLIENT_ID` matches mobile app
2. Check Google's token verification is working
3. Ensure token hasn't expired (mobile should handle this)

### Database connection error
1. Verify PostgreSQL is running: `psql postgres`
2. Check `DATABASE_URL` is correct
3. Ensure database exists: `createdb broiler_farm_db`
