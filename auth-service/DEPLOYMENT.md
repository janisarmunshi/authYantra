# Production Deployment Guide

## VPS Setup (4 cores, 8GB RAM)

### 1. Initial Server Setup

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install dependencies
sudo apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    postgresql \
    postgresql-contrib \
    nginx \
    supervisor \
    git \
    curl \
    htop

# Create non-root user for the application
sudo useradd -m -s /bin/bash authservice
sudo su - authservice
```

### 2. PostgreSQL Setup

```bash
# As root or with sudo
sudo -u postgres psql

# In PostgreSQL CLI:
CREATE DATABASE auth_service;
CREATE USER auth_user WITH PASSWORD 'strong_password_here';
ALTER ROLE auth_user SET client_encoding TO 'utf8';
ALTER ROLE auth_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE auth_user SET default_transaction_deferrable TO on;
ALTER ROLE auth_user SET default_transaction_read_uncommitted TO off;
GRANT ALL PRIVILEGES ON DATABASE auth_service TO auth_user;
\q
```

### 3. Application Setup

```bash
# As authservice user
cd /home/authservice
git clone <your-repo-url> auth-service
cd auth-service

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
ENV=production
DEBUG=False

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=auth_user
POSTGRES_PASSWORD=strong_password_here
POSTGRES_DB=auth_service

JWT_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
ENCRYPTION_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')

ENTRA_ID_TENANT_ID=
ENTRA_ID_CLIENT_ID=
ENTRA_ID_CLIENT_SECRET=

RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60
LOGIN_RATE_LIMIT=5
EOF

# Run migrations
alembic upgrade head
```

### 4. Gunicorn Setup

Create `/home/authservice/auth-service/gunicorn_config.py`:

```python
import multiprocessing

# Worker configuration
workers = (multiprocessing.cpu_count() * 4) + 2  # 18 for 4 cores
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Server mechanics
daemon = False
pidfile = "/tmp/gunicorn.pid"
umask = 0
user = "authservice"
group = "authservice"
tmp_upload_dir = None

# Logging
accesslog = "/home/authservice/auth-service/logs/access.log"
errorlog = "/home/authservice/auth-service/logs/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "auth-service"

# Server hooks
def post_fork(server, worker):
    """Post fork worker initialization"""
    pass

def when_ready(server):
    """Server is ready"""
    print("Gunicorn server is ready. Spawning workers")
```

### 5. Supervisor Setup

Create `/etc/supervisor/conf.d/auth-service.conf`:

```ini
[program:auth-service]
command=/home/authservice/auth-service/venv/bin/gunicorn -c gunicorn_config.py main:app
directory=/home/authservice/auth-service
user=authservice
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=10
stdout_logfile=/home/authservice/auth-service/logs/supervisor.log
stderr_logfile=/home/authservice/auth-service/logs/supervisor_error.log
environment=PATH="/home/authservice/auth-service/venv/bin"
```

```bash
# Create logs directory
mkdir -p /home/authservice/auth-service/logs

# Update supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start auth-service
```

### 6. Nginx Configuration

Create `/etc/nginx/sites-available/auth-service`:

```nginx
upstream auth_service {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL certificates (use Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Logging
    access_log /var/log/nginx/auth-service-access.log;
    error_log /var/log/nginx/auth-service-error.log;

    # Client limits
    client_max_body_size 10M;

    # Proxy settings
    location / {
        proxy_pass http://auth_service;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
        proxy_connect_timeout 60s;
    }

    # Health check endpoint
    location /health {
        access_log off;
        proxy_pass http://auth_service;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/auth-service /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 7. SSL Certificate (Let's Encrypt)

```bash
# Install certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Generate certificate
sudo certbot certonly --nginx -d your-domain.com

# Auto-renewal is set by default
sudo systemctl enable certbot.timer
```

### 8. PgBouncer for Connection Pooling

```bash
# Install PgBouncer
sudo apt-get install -y pgbouncer

# Configure /etc/pgbouncer/pgbouncer.ini
[databases]
auth_service = host=localhost port=5432 user=auth_user password=password dbname=auth_service

[pgbouncer]
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
min_pool_size = 10
reserve_pool_size = 5
reserve_pool_timeout = 3
max_db_connections = 100
max_user_connections = 100
server_lifetime = 3600
server_idle_timeout = 600

# Start PgBouncer
sudo systemctl start pgbouncer
sudo systemctl enable pgbouncer
```

### 9. Monitoring & Logging

**System monitoring**:
```bash
# Install node_exporter for Prometheus
wget https://github.com/prometheus/node_exporter/releases/download/v1.6.1/node_exporter-1.6.1.linux-amd64.tar.gz
tar xvfz node_exporter-1.6.1.linux-amd64.tar.gz
sudo mv node_exporter-1.6.1.linux-amd64/node_exporter /usr/local/bin/
```

**Log rotation**:

Create `/etc/logrotate.d/auth-service`:

```
/home/authservice/auth-service/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 authservice authservice
    sharedscripts
    postrotate
        sudo supervisorctl restart auth-service > /dev/null 2>&1 || true
    endscript
}
```

### 10. Backup Strategy

Create `/home/authservice/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/home/authservice/backups"
DB_NAME="auth_service"
DB_USER="auth_user"
DB_HOST="localhost"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
pg_dump -U $DB_USER -h $DB_HOST $DB_NAME | \
    gzip > $BACKUP_DIR/auth_service_$DATE.sql.gz

# Keep last 7 days of backups
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
```

Schedule in crontab:

```bash
# Daily backup at 2 AM
0 2 * * * /home/authservice/backup.sh
```

### 11. Firewall Rules

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Deny everything else
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw enable
```

### 12. Performance Tuning

**PostgreSQL** (`/etc/postgresql/*/main/postgresql.conf`):

```
shared_buffers = 2GB
effective_cache_size = 6GB
maintenance_work_mem = 512MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 10MB
```

**System limits** (`/etc/security/limits.conf`):

```
authservice soft nofile 65536
authservice hard nofile 65536
```

### 13. Health Checks & Monitoring

```bash
# Manual health check
curl https://your-domain.com/health

# Monitor service status
sudo supervisorctl status
sudo journalctl -u nginx -f
tail -f /home/authservice/auth-service/logs/error.log
```

### 14. Update & Maintenance

```bash
# Check for updates
cd /home/authservice/auth-service
git fetch origin
git pull origin main

# Update dependencies
source venv/bin/activate
pip install --upgrade -r requirements.txt

# Run migrations
alembic upgrade head

# Restart service
sudo supervisorctl restart auth-service
```

## Scaling to Multi-Server Setup

For higher loads, consider:

1. **Database**: Separate PostgreSQL server with replication
2. **Load Balancer**: HAProxy or AWS ELB
3. **Multiple App Servers**: 3-5 instances with auth-service
4. **Redis**: Cache layer for permissions and organization configs
5. **Monitoring**: Prometheus + Grafana

## Troubleshooting

**Service won't start**:
```bash
sudo supervisorctl tail -f auth-service stderr
```

**Database connection issues**:
```bash
psql -U auth_user -h localhost -d auth_service
```

**Nginx errors**:
```bash
sudo nginx -t
tail -f /var/log/nginx/error.log
```

**Memory issues**:
```bash
free -h
htop
```

Monitor and adjust worker count and pool sizes based on actual usage.
