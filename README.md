# Spielesammlung

Eine Sammlung klassischer Spiele als Flask-Webanwendung mit gemeinsamem Login.

## Spiele

- **Dame** — Brettspiel gegen KI (Minimax/Alpha-Beta) oder andere Spieler
- **Hangman** — Galgenmaennchen mit deutschen Woertern und QWERTZ-Tastatur
- **Muehle** — Brettspiel gegen KI oder Multiplayer (Echtzeit via WebSocket)
- **17 und 4** — Kartenspiel gegen den Dealer mit animiertem Kartenausteilen

## Schnellstart

```bash
./start.sh
```

Oeffne http://localhost:5000 im Browser, registriere einen Account und waehle ein Spiel.

### Manuell

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Konfiguration

Serverkonfiguration und Spielregeln in `config.ini`:

```ini
[server]
host = 0.0.0.0
port = 5000
debug = true

[twentyone]
tie_rule = dealer
num_decks = 1
dealer_stand = 17
```

## Technologie

- **Backend:** Python, Flask, Flask-SQLAlchemy, Flask-Login, Flask-SocketIO
- **Frontend:** Jinja2-Templates, Vanilla JavaScript, CSS
- **Datenbank:** SQLite
- **Echtzeit:** Socket.IO (fuer Muehle-Multiplayer)

## Tests

```bash
source venv/bin/activate
pytest tests/ -v
```

## Deployment (Produktion)

### Voraussetzungen

- Debian/Ubuntu-Server mit Python 3, nginx, systemd
- Domain oder Subdomain (fuer HTTPS via Let's Encrypt)

### Automatisches Setup

```bash
# Als root auf dem Zielserver:
sudo bash deploy/setup.sh
```

Das Script installiert alle Abhaengigkeiten, legt venv an, richtet den systemd-Service
und nginx ein. Nach dem Durchlauf sind drei manuelle Schritte noetig (werden am Ende ausgegeben).

### Manuelles Setup

#### 1. App installieren

```bash
git clone <repo-url> /opt/spielesammlung
cd /opt/spielesammlung
python3 -m venv venv
venv/bin/pip install -r requirements.txt gunicorn
chown -R www-data:www-data /opt/spielesammlung
mkdir -p /var/log/spielesammlung
chown www-data:www-data /var/log/spielesammlung
```

#### 2. Konfiguration

Debug-Modus ausschalten:

```bash
sed -i 's/^debug = true/debug = false/' /opt/spielesammlung/config.ini
```

SECRET_KEY generieren und in der Service-Datei setzen (siehe Schritt 3):

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

#### 3. systemd-Service einrichten

```bash
cp deploy/spielesammlung.service /etc/systemd/system/
```

In `/etc/systemd/system/spielesammlung.service` den generierten SECRET_KEY eintragen:

```ini
Environment=SECRET_KEY=<generierter-key>
```

Dann starten:

```bash
systemctl daemon-reload
systemctl enable --now spielesammlung
```

#### 4. nginx konfigurieren

**Variante A: Eigene (Sub-)Domain** (z.B. `spiele.example.de`)

```bash
cp deploy/spielesammlung.nginx /etc/nginx/sites-available/spielesammlung
# server_name in der Datei auf die eigene Domain aendern
ln -sf /etc/nginx/sites-available/spielesammlung /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

**Variante B: Unterpfad** (z.B. `https://meinserver.de/games`)

Den Inhalt von `deploy/spielesammlung-subpath.nginx` in den bestehenden `server{}`-Block
der nginx-Konfiguration einfuegen. Den Pfad `/games` ggf. durch den gewuenschten Pfad
ersetzen — dabei alle drei `location`-Bloecke und die `X-Forwarded-Prefix`-Header
konsistent anpassen.

```bash
nginx -t && systemctl reload nginx
```

#### 5. HTTPS aktivieren

```bash
certbot --nginx -d deine-domain.de
```

Certbot passt die nginx-Konfiguration automatisch an und richtet die Zertifikatserneuerung ein.

## Projektstruktur

```
Spielesammlung/
├── app.py              # App Factory + Entry Point
├── extensions.py       # Gemeinsame Flask-Extensions
├── models.py           # User + Spiel-Models
├── config.ini          # Konfiguration
├── auth/               # Login/Registrierung
├── dashboard/          # Spielauswahl
├── dame/               # Dame (Checkers)
├── hangman/            # Hangman
├── muehle/             # Muehle (Nine Men's Morris)
├── twentyone/          # 17 und 4
├── templates/          # Jinja2-Templates
├── static/             # CSS, JS, Bilder
└── tests/              # Pytest-Tests
```
