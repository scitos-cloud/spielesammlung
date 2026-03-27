#!/bin/bash
# Deployment-Script fuer Spielesammlung
# Ausfuehren als root auf dem Zielserver
set -e

APP_DIR=/opt/spielesammlung
LOG_DIR=/var/log/spielesammlung

echo "=== Spielesammlung Deployment ==="

# Abhaengigkeiten
apt-get update
apt-get install -y python3 python3-venv nginx certbot python3-certbot-nginx

# App-Verzeichnis
if [ ! -d "$APP_DIR" ]; then
    git clone https://github.com/scitos-cloud/spielesammlung.git "$APP_DIR"
else
    cd "$APP_DIR" && git pull
fi

# Log-Verzeichnis
mkdir -p "$LOG_DIR"
chown www-data:www-data "$LOG_DIR"

# venv + Dependencies
cd "$APP_DIR"
python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt gunicorn

# Berechtigungen
chown -R www-data:www-data "$APP_DIR"

# config.ini: debug ausschalten
sed -i 's/^debug = true/debug = false/' "$APP_DIR/config.ini"

# systemd-Service
cp "$APP_DIR/deploy/spielesammlung.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable spielesammlung
systemctl restart spielesammlung

# Nginx
cp "$APP_DIR/deploy/spielesammlung.nginx" /etc/nginx/sites-available/spielesammlung
ln -sf /etc/nginx/sites-available/spielesammlung /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

echo ""
echo "=== Deployment abgeschlossen ==="
echo ""
echo "Naechste Schritte:"
echo "  1. SECRET_KEY setzen in /etc/systemd/system/spielesammlung.service"
echo "     python3 -c \"import secrets; print(secrets.token_hex(32))\""
echo "     systemctl daemon-reload && systemctl restart spielesammlung"
echo ""
echo "  2. Domain anpassen in /etc/nginx/sites-available/spielesammlung"
echo "     server_name spiele.example.de -> deine-domain.de"
echo "     nginx -t && systemctl reload nginx"
echo ""
echo "  3. HTTPS aktivieren:"
echo "     certbot --nginx -d deine-domain.de"
