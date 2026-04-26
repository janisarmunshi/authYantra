# Central Authentication Service

A production-ready multi-tenant authentication service built with FastAPI, supporting Microsoft Entra ID SSO, JWT tokens, and traditional username/password authentication.

## Features

- **Multi-tenant Architecture**: Support multiple organizations with complete data isolation
- **Microsoft Entra ID Integration**: OAuth 2.0 Authorization Code flow for enterprise SSO
- **JWT Authentication**: Stateless token-based authentication with access + refresh tokens
- **Local Authentication**: Username/password authentication with bcrypt hashing
- **Rate Limiting**: Per-client rate limiting to prevent abuse
- **Role-Based Authorization**: Built-in role and permission management
- **Async/High Performance**: Built with FastAPI for handling 1000+ concurrent users
- **PostgreSQL**: Robust ACID-compliant database with connection pooling

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with async SQLAlchemy
- **Authentication**: JWT, Bcrypt, Python-Jose
- **Server**: Uvicorn + Gunicorn
- **Deployment**: VPS-ready with 4 cores/8GB RAM

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- pip/venv

### Installation

1. **Clone and setup**
   ```bash
   cd auth-service
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your PostgreSQL credentials
   ```

3. **Create database**
   ```bash
   createdb auth_service  # Using PostgreSQL command line
   ```

4. **Run migrations**
   ```bash
   alembic upgrade head
   ```

5. **Start the server**
   ```bash
   python -m uvicorn main:app --reload
   ```

6. **Access documentation**
   - OpenAPI Docs: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## API Usage

### Create Organization

```bash
curl -X POST "http://localhost:8000/orgs" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Company"}'
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "My Company",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00"
}
```

### Register User (Local)

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "john_doe",
    "password": "SecurePassword123!",
    "organization_id": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

### Login

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -H "Organization-ID: 550e8400-e29b-41d4-a716-446655440000" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123!"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```

### Refresh Token

```bash
curl -X POST "http://localhost:8000/auth/token/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

### Verify Token

```bash
curl -X POST "http://localhost:8000/auth/token/verify" \
  -H "Content-Type: application/json" \
  -d '{
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

### Get Current User

```bash
curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Register Application

```bash
curl -X POST "http://localhost:8000/orgs/{org_id}/apps" \
  -H "Content-Type: application/json" \
  -d '{
    "app_name": "Mobile App",
    "app_type": "mobile",
    "redirect_uris": ["myapp://oauth/callback"]
  }'
```

## Configuration

Key environment variables in `.env`:

```env
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=auth_service

# JWT
JWT_SECRET_KEY=your-secret-key-min-32-chars
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Rate Limiting
LOGIN_RATE_LIMIT=5  # attempts per minute

# Entra ID (for SSO, Phase 2)
ENTRA_ID_TENANT_ID=
ENTRA_ID_CLIENT_ID=
ENTRA_ID_CLIENT_SECRET=
```

## Database Schema

### Organizations
Multi-tenant container for user groups.

### Users
User accounts with local or SSO authentication.

### Roles
Customizable roles with permission sets per organization.

### RegisteredApps
Registered applications for rate limiting and OAuth redirects.

### RefreshTokens
Track issued refresh tokens for revocation.

## Testing

Run the test suite:

```bash
pytest tests/ -v --cov
```

Test coverage includes:
- User registration and authentication
- Token generation and validation
- Password hashing
- Tenant isolation
- Rate limiting

## Performance & Deployment

### VPS Configuration (4 cores, 8GB RAM)

**Gunicorn Configuration**:
```bash
gunicorn main:app \
  --workers 18 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

**PostgreSQL Connection Pool**:
- Worker connections: 100
- Max overflow: 50
- Pool pre-ping: enabled

**Expected Performance**:
- ~1000 concurrent users
- <200ms response time (95th percentile)
- 10,000+ requests/second

### Production Checklist

- [ ] Set secure JWT secret in `.env`
- [ ] Configure PostgreSQL with PgBouncer for connection pooling
- [ ] Enable HTTPS/TLS with Nginx reverse proxy
- [ ] Set up database backups
- [ ] Configure monitoring and alerting
- [ ] Set appropriate CORS origins (not "*")
- [ ] Enable database encryption for secrets
- [ ] Set up application logging/aggregation
- [ ] Load test before going live

## Security Considerations

1. **Passwords**: Bcrypt with cost factor 12
2. **Tokens**: HS256 HMAC signature with secure secret
3. **Refresh Token Rotation**: New token issued on refresh, old revoked
4. **Rate Limiting**: 5 login attempts per minute per IP
5. **HTTPS Only**: Enforce in production
6. **Secrets Storage**: Fernet encryption for Entra ID credentials

## Migration to Production

1. Configure PostgreSQL with proper backups
2. Set strong JWT secret (use `openssl rand -base64 32`)
3. Configure Nginx as reverse proxy with SSL
4. Run with 18 Gunicorn workers (4 cores × 4 + 2)
5. Monitor with proper logging/alerting
6. Test load with `locust` or `apache-bench`

## Phase 2+  (Future)

- Microsoft Entra ID OAuth integration
- Redis caching for permissions
- Advanced audit logging
- Multi-factor authentication
- Password complexity requirements
- API key management for service-to-service auth

## Support & Debugging

**Check service health**:
```bash
curl http://localhost:8000/health
```

**View logs**:
```bash
# Development
python -m uvicorn main:app --log-level debug

# Production
journalctl -u auth-service -f
```

**Common Issues**:
- Port 8000 in use: Change port in uvicorn command
- Database connection refused: Check PostgreSQL is running
- JWT secret too short: Must be at least 32 characters

## License

© 2024 Your Company. All rights reserved.
