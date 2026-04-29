#!/bin/bash
# One-time VPS setup for authYantra
# Run as root on the VPS: bash vps-setup.sh
set -e

REPO_URL="${1:-https://github.com/YOUR_USERNAME/authYantra.git}"
DEPLOY_DIR="/opt/authyantra"

echo "=== Installing Docker ==="
apt-get update -q
apt-get install -y curl git nginx certbot python3-certbot-nginx

curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

echo "=== Cloning repository ==="
if [ -d "$DEPLOY_DIR" ]; then
  echo "Directory exists, pulling latest..."
  cd "$DEPLOY_DIR" && git pull
else
  git clone "$REPO_URL" "$DEPLOY_DIR"
fi

echo "=== Setting up nginx ==="
ln -sf "$DEPLOY_DIR/nginx/auth.marketyantra.com.conf" /etc/nginx/sites-enabled/auth.marketyantra.com.conf
ln -sf "$DEPLOY_DIR/nginx/beta.auth.marketyantra.com.conf" /etc/nginx/sites-enabled/beta.auth.marketyantra.com.conf
rm -f /etc/nginx/sites-enabled/default

# Test nginx config (certs won't exist yet, so skip for now)
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
echo "  5. Push to main or enhancement-1 to trigger deploy"
