# authYantra - Quick Reference Guide

## 🚀 Start Services

```bash
# Start all services (Docker Compose)
docker-compose up -d

# Start specific service
docker-compose up -d auth-service
docker-compose up -d project1-backend

# View logs
docker-compose logs -f auth-service

# Stop all services
docker-compose down

# Completely clean up (WARNING: deletes all data)
docker-compose down -v
```

## 🔑 Port Reference

| Port | Service | URL |
|------|---------|-----|
| 8000 | Auth Service | http://localhost:8000 |
| 8000/docs | Auth Swagger | http://localhost:8000/docs |
| 8100 | Project 1 API | http://localhost:8100 |
| 8200 | Project 2 API | http://localhost:8200 |
| 9000 | Prometheus | http://localhost:9000 |
| 9001 | Grafana | http://localhost:9001 |
| 5432 | PostgreSQL (Auth) | localhost:5432 |
| 5433 | PostgreSQL (Project 1) | localhost:5433 |

## 🔐 API Quick Start (curl)

### Create Organization
```bash
curl -X POST http://localhost:8000/orgs \
  -H "Content-Type: application/json" \
  -d '{"name":"My Org"}'
```

### Configure Entra ID
```bash
curl -X PATCH http://localhost:8000/orgs/{ORG_ID}/entra \
  -H "Content-Type: application/json" \
  -d '{
    "entra_id_tenant_id":"your-tenant",
    "entra_id_client_id":"your-client",
    "entra_id_client_secret":"your-secret"
  }'
```

### Register User (Local Auth)
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email":"user@test.com",
    "username":"testuser",
    "password":"TestPass123!",
    "organization_id":"{ORG_ID}"
  }'
```

### Login (Local Auth)
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -H "organization_id:{ORG_ID}" \
  -d '{
    "email":"user@test.com",
    "password":"TestPass123!"
  }'

# Store the returned access_token
```

### Call Protected API
```bash
curl -X GET http://localhost:8100/api/protected \
  -H "Authorization: Bearer {ACCESS_TOKEN}"
```

## 📊 Monitoring Quick Access

```bash
# Health check all services
curl http://localhost:8000/health
curl http://localhost:8100/health

# Prometheus metrics query
curl http://localhost:9000/api/v1/query?query=http_requests_total

# View logs for all services
docker-compose logs -f

# View logs for specific service
docker-compose logs -f --tail=50 auth-service
```

## 🔄 Development Workflow

### Making Changes to Auth Service

```bash
# Edit code
vim auth-service/routes/auth.py

# Restart service
docker-compose restart auth-service

# Or for hot reload (if enabled)
# Changes auto-load
```

### Running Database Migrations

```bash
# Create new migration
cd auth-service
alembic revision --autogenerate -m "Add new column"

# Apply migrations
alembic upgrade head

# Check status
alembic current
```

### Running Tests

```bash
cd auth-service
pytest tests/ -v
pytest tests/test_auth.py -v
pytest tests/ --cov=services
```

## 🔑 Important Environment Variables

```env
# MUST MATCH ACROSS ALL SERVICES
JWT_SECRET_KEY=your-32-char-minimum-secret-key

# Entra ID Redirect URI Must Be Registered in Azure
ENTRA_ID_REDIRECT_URI=http://localhost:9000/auth/callback

# Database URLs
POSTGRES_HOST=postgres-auth
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

## ❌ Common Issues & Fixes

### "Port already in use"
```bash
# Kill process on port 8000
# Windows:
netstat -ano | find "8000"
taskkill /PID {PID} /F

# Mac/Linux:
lsof -i :8000
kill -9 {PID}
```

### "Connection refused to database"
```bash
# Check PostgreSQL is running
docker-compose ps postgres-auth

# Restart it
docker-compose restart postgres-auth
```

### "Invalid token"
```
Check:
1. Token not expired (exp claim)
2. Authorization header format: "Bearer TOKEN"
3. JWT_SECRET_KEY matches across services
4. Token type is "access" not "refresh"
```

### "CORS error in browser"
```
Setup frontend correctly:
1. Serve from backend (recommended)
2. Or configure CORS in backend .env:
   CORS_ORIGINS=["http://localhost:3000"]
```

## 📈 Performance Checks

```bash
# Response time (check for slow queries)
docker-compose logs auth-service | grep "response_time"

# Error rate
curl http://localhost:9000/metrics | grep http_requests_total

# Database connections
curl http://localhost:9000/metrics | grep postgres_connections
```

## 🔐 Security Checklist

```
✅ Local Development:
  □ Use simple passwords
  □ Allow CORS from localhost
  □ Use HTTP (OK for local)
  
✅ Before Production:
  □ Generate strong JWT_SECRET_KEY
  □ Enable HTTPS/SSL
  □ Restrict CORS origins
  □ Enable request logging
  □ Set up monitoring alerts
  □ Backup database
  □ Test disaster recovery
```

## 📚 Documentation Files

- **PORT-ALLOCATION.md** - Detailed port strategy and multi-org setup
- **SETUP-GUIDE.md** - Complete setup and deployment guide
- **ENTRA_ID_INTEGRATION.md** - OAuth/Entra ID configuration
- **README.md** - This file

## 🤔 Need Help?

1. Check logs: `docker-compose logs -f {service-name}`
2. Check port allocation: See PORT-ALLOCATION.md
3. Check API docs: http://localhost:8000/docs
4. Review environment variables in .env
5. Verify JWT_SECRET_KEY matches across services

## 🚢 Common Commands

```bash
# View running processes
docker-compose ps

# Get service status
docker-compose exec auth-service curl http://localhost/health

# Access database directly
docker-compose exec postgres-auth psql -U postgres -d authYantra

# Rebuild service
docker-compose up -d --build auth-service

# Remove old images
docker image prune -f

# Check resource usage
docker stats
```

## 💾 Backup & Restore

```bash
# Backup database
docker-compose exec postgres-auth pg_dump -U postgres authYantra > backup.sql

# Restore database
docker-compose exec -T postgres-auth psql -U postgres authYantra < backup.sql
```

---

**Quick Tips:**
- 🎯 Always check logs first: `docker-compose logs -f`
- 🔑 JWT_SECRET_KEY must be 32+ chars and match everywhere
- 🌐 Frontend should be served from backend (not separate port)
- 📊 Prometheus available at http://localhost:9000
- 📢 All API docs available in Swagger UI (*/docs)

**Last Updated:** March 8, 2026
