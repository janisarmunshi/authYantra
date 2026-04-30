#!/bin/bash
# One-time VPS setup for authYantra
# Usage: bash vps-setup.sh [repo_url] [branch]
# Example: bash vps-setup.sh https://github.com/janisarmunshi/authYantra.git dev
set -euo pipefail 

REPO_URL="${1:-https://github.com/janisarmunshi/authYantra.git}"
BRANCH="${2:-main}"
DEPLOY_DIR="/opt/authyantra"

if [ "$EUID" -ne 0 ]; then
  echo "Please run this script as root."
  exit 1
fi

echo "=== Installing dependencies ==="
apt-get update -q
apt-get install -y curl git nginx certbot python3-certbot-nginx

echo "=== Installing Docker ==="
if command -v docker >/dev/null 2>&1; then
  echo "Docker already installed: $(docker --version)"
else
  apt-get install -y docker.io
fi
systemctl enable docker
systemctl start docker

echo "=== Installing Docker Compose v2 ==="
if docker compose version >/dev/null 2>&1; then
  echo "Docker Compose already installed: $(docker compose version)"
else
  mkdir -p /usr/local/lib/docker/cli-plugins
  curl -SL https://github.com/docker/compose/releases/download/v2.27.0/docker-compose-linux-x86_64 \
       -o /usr/local/lib/docker/cli-plugins/docker-compose
  chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
  echo "Installed: $(docker compose version)"
fi

echo "=== Cloning or updating repository ==="
if [ -d "$DEPLOY_DIR" ]; then
  echo "Directory exists, syncing branch '$BRANCH'..."
  cd "$DEPLOY_DIR"
  git fetch origin --prune
  if git rev-parse --verify --quiet "refs/heads/$BRANCH" >/dev/null; then
    git checkout "$BRANCH"
  else
    git checkout -B "$BRANCH" "origin/$BRANCH"
  fi
  git pull --ff-only origin "$BRANCH"
else
  git clone --branch "$BRANCH" --single-branch "$REPO_URL" "$DEPLOY_DIR"
fi

echo "=== Setting up nginx ==="
ln -sf "$DEPLOY_DIR/nginx/auth.marketyantra.com.conf" /etc/nginx/sites-enabled/auth.marketyantra.com.conf
ln -sf "$DEPLOY_DIR/nginx/beta.auth.marketyantra.com.conf" /etc/nginx/sites-enabled/beta.auth.marketyantra.com.conf
rm -f /etc/nginx/sites-enabled/default

echo "=== Obtaining SSL certificates ==="
echo "Run these after DNS is pointing to this server:"
echo "  certbot --nginx -d auth.marketyantra.com"
echo "  certbot --nginx -d beta.auth.marketyantra.com"

echo ""
echo "=== Setup complete ==="
echo "Next steps:"
echo "  1. Add DNS A records: auth.marketyantra.com → 103.212.121.121"
echo "                        beta.auth.marketyantra.com → 103.212.121.121"
echo "  2. Run: certbot --nginx -d auth.marketyantra.com -d beta.auth.marketyantra.com"
echo "  3. Run: nginx -t && systemctl reload nginx"
echo "  4. Add GitHub secrets (see deploy.yml comments)"
echo "  5. Use the second argument to choose branch: main or dev"
