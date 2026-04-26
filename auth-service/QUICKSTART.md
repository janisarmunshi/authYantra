# Quick Start Guide

Get up and running with the Auth Service in 5 minutes.

## Option 1: Docker Compose (Easiest)

```bash
cd auth-service

# Copy environment file
cp .env.example .env

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f auth-service

# Access API
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

## Option 2: Manual Setup

### 1. Install PostgreSQL

**Ubuntu/Debian**:
```bash
sudo apt-get install postgresql postgresql-contrib
```

**macOS**:
```bash
brew install postgresql
brew services start postgresql
```

**Windows**:
Download from [postgresql.org](https://www.postgresql.org/download/windows/)

### 2. Create Database

```bash
# As postgres user
sudo -u postgres psql

# In PostgreSQL:
CREATE DATABASE auth_service;
\q
```

### 3. Setup Python Environment

```bash
# Clone/navigate to project
cd auth-service

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment
cp .env.example .env

# Run migrations
alembic upgrade head

# Start server
python -m uvicorn main:app --reload
```

Server runs at: **http://localhost:8000**

## First API Calls

### 1. Create Organization

```bash
curl -X POST http://localhost:8000/orgs \
  -H "Content-Type: application/json" \
  -d '{"name": "My Company"}'

# Save the returned `id` as ORG_ID
```

### 2. Register User

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "john",
    "password": "SecurePass123!",
    "organization_id": "ORG_ID"
  }'
```

### 3. Login

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -H "Organization-ID: ORG_ID" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'

# Save returned `access_token` and `refresh_token`
```

### 4. Use Access Token

```bash
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer ACCESS_TOKEN"
```

### 5. Refresh Token

```bash
curl -X POST http://localhost:8000/auth/token/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "REFRESH_TOKEN"}'
```

## Development Commands

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_auth.py

# With coverage
pytest --cov=.

# Watch mode
pytest-watch tests/
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1

# Check migration status
alembic current
```

### API Documentation

Interactive docs automatically available:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Debugging

```bash
# Add to Python code:
import pdb; pdb.set_trace()

# Or use breakpoint() in Python 3.7+
breakpoint()

# View logs in real-time
tail -f logs/debug.log
```

## Common Issues

**Port 8000 in use**:
```bash
python -m uvicorn main:app --port 8001
```

**Database connection refused**:
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql  # Linux
brew services list | grep postgres  # macOS

# Check connection
psql -U postgres -d auth_service
```

**Module not found errors**:
```bash
# Ensure virtual env is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

**Alembic migration issues**:
```bash
# Reset to initial state (for dev only!)
alembic downgrade --sql base

# Then reapply
alembic upgrade head
```

## Project Structure

```
auth-service/
├── main.py                 # FastAPI app entry point
├── config.py              # Configuration & settings
├── database.py            # Database connection
├── models.py              # SQLAlchemy ORM models
├── schemas.py             # Pydantic validation schemas
├── routes/                # API endpoints
│   ├── auth.py           # Authentication routes
│   └── health.py         # Health & management
├── services/             # Business logic
│   ├── user_service.py
│   ├── token_service.py
│   └── rate_limiter.py
├── middleware/           # Custom middleware
├── migrations/           # Database migrations (Alembic)
├── tests/               # Test suite
├── requirements.txt
├── .env.example
└── README.md
```

## Next Steps

1. **For Development**: Continue implementing features from Phase 2-4
2. **For Deployment**: Follow [DEPLOYMENT.md](./DEPLOYMENT.md)
3. **For Integration**: Review API endpoints in Swagger at `/docs`

## Need Help?

Check the full [README.md](./README.md) for:
- Complete API reference
- Configuration options
- Security considerations
- Production deployment guide

Happy coding! 🚀
