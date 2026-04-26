# authYantra - Multi-Organization, Multi-Project Authentication Platform

Complete setup and deployment guide for a scalable, multi-tenant identity service with support for multiple projects and organizations.

## 📋 Overview

authYantra is a centralized authentication and authorization platform designed for:

- ✅ **Multiple Organizations**: Each organization has its own Entra ID configuration
- ✅ **Multiple Projects**: Support for unlimited backend applications
- ✅ **JWT-based**: Stateless token verification, no round-trips needed
- ✅ **Microsoft Entra ID Integration**: OAuth 2.0 with PKCE support
- ✅ **Multi-tenant**: Complete data isolation by organization
- ✅ **Production-Ready**: Includes monitoring, logging, and API gateway

## 📁 Project Structure

```
authYantra/
├── auth-service/                 # Central identity service (Port 8000)
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── config.py
│   ├── routes/
│   │   ├── auth.py              # Local auth endpoints
│   │   ├── entra_id.py          # OAuth endpoints
│   │   └── health.py            # Health checks
│   ├── services/
│   │   ├── user_service.py
│   │   ├── token_service.py
│   │   └── entra_id_service.py
│   ├── migrations/              # Alembic migrations
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env
│
├── projects/
│   ├── project1/
│   │   └── backend/             # Project 1 Backend (Port 8100)
│   │       ├── main.py
│   │       ├── requirements.txt
│   │       └── .env
│   │
│   └── project2/
│       └── backend/             # Project 2 Backend (Port 8200)
│           ├── main.py
│           ├── requirements.txt
│           └── .env
│
├── monitoring/
│   ├── nginx.conf               # API Gateway configuration
│   └── prometheus.yml           # Metrics configuration
│
├── docker-compose.yml           # Complete infrastructure setup
├── PORT-ALLOCATION.md           # Port numbering strategy
├── SETUP.md                     # Deployment guide
└── README.md                    # This file
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Python 3.12+ (for local development)
- PostgreSQL 15+ (if running without Docker)
- Azure account with Entra ID configured (for OAuth)

### Option 1: Using Docker Compose (Recommended)

```bash
# 1. Clone the repository
git clone <repo-url>
cd authYantra

# 2. Build and start all services
docker-compose up -d

# 3. Verify services are running
docker-compose ps
```

**Services running on:**
- Auth Service: http://localhost:8000
- Auth Service Docs: http://localhost:8000/docs
- Project 1 API: http://localhost:8100
- Project 2 API: http://localhost:8200
- Prometheus: http://localhost:9000
- Grafana: http://localhost:9001
- API Gateway: https://localhost (with Nginx)

### Option 2: Local Development

```bash
# 1. Create virtual environment
python -m venv envAuth
source envAuth/Scripts/activate  # or `envAuth\Scripts\activate` on Windows

# 2. Install dependencies
cd auth-service
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your settings

# 4. Run migrations
alembic upgrade head

# 5. Start the server
python main.py
# or with uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## ⚙️ Configuration

### Environment Variables

**Auth Service (.env)**
```env
ENV=development
DEBUG=True

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=authYantra

# JWT - IMPORTANT: Must match across all services
JWT_SECRET_KEY=your-very-long-secret-key-32-chars-minimum-production-only
JWT_ALGORITHM=HS256

# Entra ID (optional - configure per-org via API)
ENTRA_ID_TENANT_ID=your-tenant-id
ENTRA_ID_CLIENT_ID=your-client-id
ENTRA_ID_CLIENT_SECRET=your-client-secret
```

**Project Backend (.env)**
```env
ENV=development
DEBUG=True

# Database (separate from auth service)
POSTGRES_HOST=localhost
POSTGRES_PORT=5433  # Different port
POSTGRES_USER=project1_user
POSTGRES_PASSWORD=project1_password
POSTGRES_DB=project1_db

# Auth Service Communication
AUTH_SERVICE_URL=http://localhost:8000

# JWT - MUST MATCH Auth Service
JWT_SECRET_KEY=your-very-long-secret-key-32-chars-minimum-production-only
```

### Port Allocation

See [PORT-ALLOCATION.md](PORT-ALLOCATION.md) for detailed port mapping strategy.

**Quick Reference:**
- **8000**: Auth Service
- **8100-8199**: Project 1 services
- **8200-8299**: Project 2 services
- **9000-9499**: Infrastructure/monitoring

## 📱 API Usage

### 1. Register Organization

```bash
curl -X POST http://localhost:8000/orgs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Organization",
    "entra_id_tenant_id": "optional-tenant-id"
  }'

# Response:
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "My Organization",
  "entra_id_tenant_id": null,
  "is_active": true,
  "created_at": "2026-03-08T12:00:00"
}
```

### 2. Configure Entra ID for Organization

```bash
curl -X PATCH http://localhost:8000/orgs/{org_id}/entra \
  -H "Content-Type: application/json" \
  -d '{
    "entra_id_tenant_id": "your-tenant-id",
    "entra_id_client_id": "your-client-id",
    "entra_id_client_secret": "your-client-secret"
  }'
```

### 3. User Registration (Local Auth)

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "username",
    "password": "SecurePassword123!",
    "organization_id": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

### 4. User Login (Local Auth)

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -H "organization_id: 550e8400-e29b-41d4-a716-446655440000" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123!"
  }'

# Response:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 900
}
```

### 5. OAuth with Entra ID

```bash
# Step 1: Get authorization URL
curl "http://localhost:8000/auth/entra/authorize?organization_id={org_id}&redirect_uri=http://localhost:9000/auth/callback"

# Response:
{
  "authorization_url": "https://login.microsoftonline.com/...",
  "state": "..."
}

# Step 2: Open authorization_url in browser, user logs in
# Step 3: Exchange code for tokens
curl "http://localhost:8000/auth/entra/callback?code={code}&state={state}&organization_id={org_id}"
```

### 6. Call Protected API (Project Backend)

```bash
# With JWT token from auth service
curl -X GET http://localhost:8100/api/protected-endpoint \
  -H "Authorization: Bearer {jwt_token}"

# Backend verifies token locally (NO call to auth service)
```

## 🔐 Security Best Practices

### Development
- Use simple passwords
- Allow CORS from localhost
- Enable debug logging
- Use HTTP (not HTTPS)

### Staging
- Use strong passwords
- Restrict CORS origins
- Enable audit logging
- Use self-signed HTTPS certificates

### Production
- 🔴 **NEVER** commit `.env` files
- Use environment-specific secrets management (Vault, AWS Secrets Manager)
- Enable HTTPS with valid certificates (Let's Encrypt)
- Restrict CORS to specific origins
- Use strong JWT_SECRET_KEY (32+ characters, random)
- Rotate JWT_SECRET_KEY periodically
- Enable WAF (Web Application Firewall)
- Use VPC/network isolation
- Enable request logging and monitoring
- Set up alerts for suspicious activity

### Token Security
```
⚠️ JWT_SECRET_KEY is critical:
  ├─ Must be identical across ALL services
  ├─ Must be 32+ characters
  ├─ Must be truly random
  ├─ Must NEVER be committed to git
  ├─ Must be rotated quarterly
  └─ Must be stored in secure vault
```

## 🗄️ Database Management

### Run Migrations

```bash
cd auth-service

# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Check migration status
alembic current
alembic history
```

### Reset Database (Development Only)

```bash
# Warning: This deletes ALL data
alembic downgrade base
alembic upgrade head
```

## 📊 Monitoring

### Prometheus Metrics

Visit http://localhost:9000 to query metrics:
```promql
# Request rate (requests per second)
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m])

# Response time (p95)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

### Grafana Dashboards

Visit http://localhost:9001
- Default login: admin/admin
- Add Prometheus datasource: http://prometheus:9090

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f auth-service
docker-compose logs -f project1-backend

# Last 100 lines
docker-compose logs --tail=100 auth-service
```

## 🧪 Testing

### Run Tests

```bash
cd auth-service
pytest tests/

# With coverage
pytest tests/ --cov=services --cov-report=html
```

### Manual Testing with Postman

1. Import collection: `./postman-collection.json`
2. Configure environment:
   - `auth_url`: http://localhost:8000
   - `project1_url`: http://localhost:8100
   - `org_id`: {your-org-id}
3. Run preset request sequences

## 🚢 Deployment

### Docker

```bash
# Build images
docker build -t authyantra/auth-service:latest auth-service/

# Push to registry
docker tag authyantra/auth-service:latest myregistry.azurecr.io/authyantra/auth-service:latest
docker push myregistry.azurecr.io/authyantra/auth-service:latest
```

### Kubernetes

See `k8s/` directory for Kubernetes manifests:
```bash
kubectl apply -f k8s/auth-service/
kubectl apply -f k8s/project1/
kubectl apply -f k8s/project2/
```

## 📚 API Documentation

- **Auth Service Swagger UI**: http://localhost:8000/docs
- **Auth Service ReDoc**: http://localhost:8000/redoc
- **Project 1 Swagger UI**: http://localhost:8100/docs
- **Project 2 Swagger UI**: http://localhost:8200/docs
- **Documentation Portal**: http://localhost/docs

## 🔧 Troubleshooting

### Service won't start

```bash
# Check logs
docker-compose logs auth-service

# Check port availability
netstat -ano | grep 8000  # Windows
lsof -i :8000            # Mac/Linux

# Restart service
docker-compose restart auth-service
```

### Database connection error

```bash
# Check PostgreSQL is running
docker-compose logs postgres-auth

# Verify connection string in .env
# Format: postgresql://user:password@host:port/db
```

### Token verification fails

```
❌ "Invalid or expired token"
  └─ Check JWT_SECRET_KEY matches across services
  └─ Check token hasn't expired (ACCESS_TOKEN_EXPIRE_MINUTES)
  └─ Check Authorization header format: "Bearer {token}"
```

### CORS errors in browser

```bash
# Frontend: 8001
# Backend: 8100
# ❌ Different origins = CORS issue

# Solution:
# 1. Serve frontend from backend (recommended)
# 2. Or configure CORS in backend:
CORS_ORIGINS=["http://localhost:8001"]
```

## 📖 Additional Resources

- [PORT-ALLOCATION.md](PORT-ALLOCATION.md) - Port numbering strategy
- [SETUP.md](./auth-service/SETUP.md) - Detailed setup guide
- [ENTRA_ID_INTEGRATION.md](./auth-service/ENTRA_ID_INTEGRATION.md) - OAuth setup
- [API Documentation](http://localhost:8000/docs) - Interactive Swagger UI

## ✅ Checklist for Production

- [ ] Generate strong JWT_SECRET_KEY (32+ chars, random)
- [ ] Configure SSL/TLS certificates (Let's Encrypt)
- [ ] Set up WAF (Web Application Firewall)
- [ ] Enable request logging to centralized log service (ELK Stack)
- [ ] Configure alerts (PagerDuty, Slack, etc.)
- [ ] Set up backup/restore procedures for PostgreSQL
- [ ] Enable database encryption at rest
- [ ] Configure rate limiting across all endpoints
- [ ] Set up monitoring dashboards (Grafana)
- [ ] Document runbooks for common issues
- [ ] Test disaster recovery procedures
- [ ] Set up CI/CD pipeline (GitHub Actions, Azure Pipelines)
- [ ] Configure secrets management (Azure Key Vault)
- [ ] Enable audit logging
- [ ] Conduct security penetration testing

## 📝 License

internal

## 👥 Support

For questions or issues:
1. Check troubleshooting section above
2. Review logs: `docker-compose logs -f`
3. Check port allocation: [PORT-ALLOCATION.md](PORT-ALLOCATION.md)
4. Review API docs: http://localhost:8000/docs

---

**Version**: 1.0  
**Last Updated**: March 8, 2026  
**Status**: Production Ready
