#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════
#  AI Radio — VPS setup script (Ubuntu 22.04)
#  Run once as root on a fresh Hetzner/DigitalOcean server.
#  Usage: bash scripts/deploy_vps.sh
# ══════════════════════════════════════════════════════════════
set -euo pipefail

APP_DIR="/opt/ai-radio"
APP_USER="airadio"

echo "==> Creating system user"
id -u $APP_USER &>/dev/null || useradd -m -s /bin/bash $APP_USER

echo "==> Installing system dependencies"
apt-get update -q
apt-get install -y -q python3.11 python3.11-venv python3-pip nodejs npm nginx certbot python3-certbot-nginx git

echo "==> Installing PM2 globally"
npm install -g pm2

echo "==> Cloning / updating repo"
if [ -d "$APP_DIR/.git" ]; then
    git -C "$APP_DIR" pull
else
    git clone . "$APP_DIR"
fi
chown -R $APP_USER:$APP_USER "$APP_DIR"

echo "==> Python venv + dependencies"
sudo -u $APP_USER bash -c "
    cd $APP_DIR
    python3.11 -m venv .venv
    .venv/bin/pip install -q --upgrade pip
    .venv/bin/pip install -q -r requirements.txt
"

echo "==> Next.js build"
sudo -u $APP_USER bash -c "
    cd $APP_DIR/web
    npm ci --silent
    npm run build
"

echo "==> PM2 ecosystem config"
cat > /opt/ai-radio/ecosystem.config.js << 'EOF'
module.exports = {
  apps: [{
    name: 'ai-radio-web',
    cwd: '/opt/ai-radio/web',
    script: 'node_modules/.bin/next',
    args: 'start -p 3000',
    env: { NODE_ENV: 'production' },
    restart_delay: 5000,
    max_restarts: 10,
  }],
};
EOF

echo "==> Starting Next.js with PM2"
sudo -u $APP_USER bash -c "
    cd /opt/ai-radio
    pm2 start ecosystem.config.js
    pm2 save
"
pm2 startup systemd -u $APP_USER --hp /home/$APP_USER | tail -1 | bash

echo "==> Installing midnight cron job"
(crontab -u $APP_USER -l 2>/dev/null; echo "0 0 * * * cd $APP_DIR && .venv/bin/python -m pipeline.run_daily >> logs/cron.log 2>&1") \
    | crontab -u $APP_USER -

echo "==> Nginx config"
cat > /etc/nginx/sites-available/ai-radio << 'NGINX'
server {
    listen 80;
    server_name _;

    # Security headers (Nginx layer)
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options DENY always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;

    # Gzip
    gzip on;
    gzip_types text/plain application/json application/javascript text/css;

    location / {
        proxy_pass         http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection 'upgrade';
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_cache_bypass $http_upgrade;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/ai-radio /etc/nginx/sites-enabled/ai-radio
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Copy your .env to $APP_DIR/.env"
echo "  2. Run: certbot --nginx -d your-domain.com"
echo "  3. Test pipeline: sudo -u $APP_USER bash -c 'cd $APP_DIR && .venv/bin/python -m pipeline.run_daily --seed-mock'"
echo "  4. Check Next.js: pm2 logs ai-radio-web"
