# Port Allocation Strategy for authYantra

This document defines the port allocation strategy for all services across the authYantra platform, supporting multiple organizations and projects with clear hierarchical organization.

## Overview

```
┌─────────────────────────────────────────────────────────┐
│           PORT ALLOCATION HIERARCHY                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  CORE SERVICES (8000-8099)                              │
│  ├─ 8000: Identity/Auth Service                        │
│  └─ 8001-8009: Auth dependencies (Redis, DB, etc.)     │
│                                                          │
│  PROJECT BANDS (100 ports each)                         │
│  ├─ 8100-8199: Project 1 (e.g., Main App)              │
│  ├─ 8200-8299: Project 2 (e.g., Analytics)             │
│  ├─ 8300-8399: Project 3 (e.g., Reports)               │
│  └─ 8X00-8X99: Additional Projects                     │
│                                                          │
│  INFRASTRUCTURE (9000-9499)                             │
│  ├─ 9000: Prometheus (Metrics)                         │
│  ├─ 9001: Grafana (Dashboards)                         │
│  ├─ 9005: API Gateway/Load Balancer                    │
│  └─ 9010-9499: Reserved                                │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Detailed Port Mapping

### Core Services (8000-8099)

| Port | Service | Purpose | Status |
|------|---------|---------|--------|
| 8000 | Auth Service | Central authentication & OAuth | Active |
| 8001 | Redis Cache | Token / Session cache | Optional |
| 8002 | PostgreSQL | Identity database | Optional |
| 8003-8009 | Reserved | Future auth dependencies | Reserved |

### Project Bands (8100-8X99)

Each project gets a **100-port band** with standardized port assignments:

#### Project 1 Band (8100-8199)
**Example: Main Application / E-Commerce**

| Port | Service | Purpose | Notes |
|------|---------|---------|-------|
| 8100 | Backend API | Main business logic | Production |
| 8101 | Frontend | React/Vue/Angular app | Dev only* |
| 8102 | Worker Service | Background jobs/queues | Optional |
| 8103 | WebSocket Service | Real-time updates | Optional |
| 8104 | Redis Cache | Session/data cache | Optional |
| 8105 | Message Queue | RabbitMQ/Kafka broker | Optional |
| 8110-8119 | Staging Backend | Staging environment | Testing |
| 8120-8129 | Staging Frontend | Staging environment | Testing |
| 8130-8139 | Dev Backend | Development/testing | Dev |
| 8140-8149 | Dev Frontend | Development/testing | Dev |
| 8150-8199 | Reserved | Future sub-services | Reserved |

**Auth Service Communication**:
```
Project 1 Backend (8100)
   ├─ Talks to Auth Service (8000)
   └─ Uses shared JWT_SECRET_KEY for token verification
```

#### Project 2 Band (8200-8299)
**Example: Analytics Service**

| Port | Service | Purpose |
|------|---------|---------|
| 8200 | Backend API | Analytics business logic |
| 8201 | Frontend | Analytics dashboard |
| 8202 | Worker Service | Report generation jobs |
| 8210-8219 | Staging | Staging environment |
| 8230 | Redis Cache | Analytics cache |

#### Project 3 Band (8300-8399)
**Example: Reports Service**

| Port | Service | Purpose |
|------|---------|---------|
| 8300 | Backend API | Reports generation |
| 8301 | Frontend | Reports UI |
| 8302 | Report Engine | Async report processing |

#### Future Projects
- Project 4: 8400-8499
- Project 5: 8500-8599
- Project N: 8X00-8X99

### Infrastructure Services (9000-9499)

| Port | Service | Purpose | Optional |
|------|---------|---------|----------|
| 9000 | Prometheus | Metrics collection | Yes |
| 9001 | Grafana | Metrics visualization | Yes |
| 9002 | ELK Stack | Logging aggregation | Yes |
| 9005 | Nginx/API Gateway | Reverse proxy load balancer | No |
| 9010-9499 | Reserved | Future infrastructure | Reserved |

## Naming Convention

### Service Names
```
Format: {project}-{service-type}-{environment}

Examples:
- authYantra-auth-service       (Identity service)
- project1-api-prod             (Project 1 backend production)
- project1-worker-prod          (Project 1 worker job service)
- project1-frontend-dev         (Project 1 frontend development)
- project2-api-staging          (Project 2 backend staging)
```

### Environment Tags
```
- prod    : Production environment (8X00 ports)
- staging : Staging environment (8X10-8X19 ports)
- dev     : Development environment (8X30-8X49 ports)
- local   : Local testing (any assigned port)
```

## Multi-Organization Setup

For supporting multiple organizations within the same project:

```
Organization A
  └─ Project 1 (8100)
     ├─ Org A Tenant ID: UUID
     ├─ Entra ID Config: Stored in DB
     └─ Users: Isolated by org_id

Organization B
  └─ Project 1 (8100) — SAME BACKEND
     ├─ Org B Tenant ID: UUID
     ├─ Entra ID Config: Stored in DB
     └─ Users: Isolated by org_id

Organization C
  └─ Project 2 (8200)
     ├─ Different backend, same auth service
     └─ Token verified using shared JWT_SECRET_KEY
```

**Key Point**: All organizations use the **same auth service (8000)** and **same JWT verification key**, but maintain data isolation through `organization_id` in the database.

## Authentication Flow (Multi-Org)

```
User at Organization A
      │
      ├─ Requests: GET /auth/entra/authorize?org_id=ORG_A_UUID&redirect_uri=...
      │   (to Auth Service 8000)
      │
      ├─ Logs in with Microsoft
      │
      ├─ Receives JWT with org_id=ORG_A_UUID in claims
      │
      ├─ Stores JWT in frontend
      │
      └─ Calls Project 1 Backend (8100) with JWT
         └─ Backend verifies JWT locally (no round-trip to auth service)
            └─ Extracts org_id from JWT to ensure tenant isolation
```

## Environment-Specific Configurations

### Development Environment
- Use ports: 8130-8149 (project 1), 8230-8249 (project 2), etc.
- Shared single PostgreSQL (8002)
- Hot reload enabled
- Debug logging enabled

### Staging Environment
- Use ports: 8110-8119 (project 1), 8210-8219 (project 2), etc.
- Separate PostgreSQL database
- Testing authentication
- Performance monitoring

### Production Environment
- Use ports: 8100 (project 1), 8200 (project 2), etc.
- Behind API Gateway (9005)
- Managed by Kubernetes/Docker Swarm
- No direct port access (only through reverse proxy)

## Configuration Examples

### Auth Service (.env)
```env
# Auth Service - runs on 8000
ENV=production
DEBUG=False
PORT=8000

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure-password
POSTGRES_DB=authYantra

JWT_SECRET_KEY=your-very-long-secret-key-32-chars-minimum-production-only
JWT_ALGORITHM=HS256

ENTRA_ID_AUTHORITY=https://login.microsoftonline.com
ENTRA_ID_SCOPE=https://graph.microsoft.com/.default
ENTRA_ID_RESPONSE_TYPE=code
ENTRA_ID_RESPONSE_MODE=query
OAUTH_STATE_EXPIRY=600
```

### Project 1 Backend (.env)
```env
# Project 1 - runs on 8100
ENV=production
DEBUG=False
PORT=8000  # Internal port
EXPOSE_PORT=8100  # External port

# Must match Auth Service's JWT_SECRET_KEY
JWT_SECRET_KEY=your-very-long-secret-key-32-chars-minimum-production-only

# Auth Service URL (internal communication)
AUTH_SERVICE_URL=http://localhost:8000

# Database (can be separate from auth service DB)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=project1_user
POSTGRES_PASSWORD=project1-password
POSTGRES_DB=project1_db
```

### Project 2 Backend (.env)
```env
# Project 2 - runs on 8200
ENV=production
DEBUG=False
PORT=8000  # Internal port
EXPOSE_PORT=8200  # External port

# Must match Auth Service's JWT_SECRET_KEY
JWT_SECRET_KEY=your-very-long-secret-key-32-chars-minimum-production-only

# Auth Service URL
AUTH_SERVICE_URL=http://localhost:8000

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=project2_user
POSTGRES_PASSWORD=project2-password
POSTGRES_DB=project2_db
```

## Scaling Considerations

### Horizontal Scaling
When running multiple instances of the same service:
```
Project 1 Backend (Load Balanced)
  ├─ Instance 1: 8100
  ├─ Instance 2: 8100 (via Docker/Kubernetes)
  └─ Instance 3: 8100 (via Docker/Kubernetes)
     └─ All behind Nginx (9005)
```

### Kubernetes Deployment
```yaml
# In K8s, external ports don't matter
# Use internal port (8000) and let service discovery handle it
# Nginx ingress maps external URLs to internal services
```

## Security Notes

⚠️ **In Production**:
1. **Never expose internal ports directly** (8100, 8200, etc.)
2. **Use Nginx/API Gateway (9005)** to proxy all requests
3. **Use HTTPS only** (configure SSL certificates)
4. **Firewall rules** should only allow port 443 (HTTPS) and 80 (HTTP redirect)
5. **JWT_SECRET_KEY** must be:
   - Identical across all services
   - At least 32 characters
   - Rotated periodically
   - Stored securely (not in git)

Example Nginx configuration:
```nginx
upstream auth_service {
    server localhost:8000;
}

upstream project1_api {
    server localhost:8100;
}

upstream project2_api {
    server localhost:8200;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;
    
    ssl_certificate /etc/ssl/certs/certificate.crt;
    ssl_certificate_key /etc/ssl/private/key.key;
    
    location /auth {
        proxy_pass http://auth_service;
    }
    
    location /project1 {
        proxy_pass http://project1_api;
    }
    
    location /project2 {
        proxy_pass http://project2_api;
    }
}
```

## Monitoring & Health Checks

Each service should expose health endpoints:

```bash
# Auth Service
curl http://localhost:8000/health

# Project 1 Backend
curl http://localhost:8100/health

# Project 2 Backend
curl http://localhost:8200/health

# Prometheus metrics
curl http://localhost:9000/metrics
```

## Documentation Tracking

Last Updated: March 8, 2026
Maintained By: Development Team
Version: 1.0

### Changes Log
- v1.0: Initial port allocation strategy defined
- Future: Update as new projects are added
