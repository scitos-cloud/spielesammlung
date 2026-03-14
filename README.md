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
