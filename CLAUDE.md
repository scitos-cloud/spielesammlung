# CLAUDE.md

## Projekt

Spielesammlung — Flask-Webanwendung mit sechs Spielen unter einem gemeinsamen Login. Sprache im Code: Englisch. UI-Texte: Deutsch.

## Build & Run

```bash
./start.sh
# oder manuell:
source venv/bin/activate
python app.py
```

Server startet auf http://localhost:5000 (konfigurierbar in config.ini).

## Tests

```bash
source venv/bin/activate
pytest tests/ -v
```

## Architektur

- **Flask App Factory** in `app.py` mit `socketio.run()` (noetig fuer Muehle-Multiplayer)
- **Gemeinsame Extensions** in `extensions.py`: db, login_manager, socketio, csrf
- **Ein User-Model** in `models.py` (Username + Passwort), dazu spielspezifische Models (DameGame, MuehleGame, MuehleGameMove, BackgammonGame, MauMauRoom, MauMauGameLog, MauMauGameLogPlayer)
- **SQLite-Datenbank**: `instance/spielesammlung.db`, angelegt via `db.create_all()`

### Blueprints

| Blueprint | Prefix | Beschreibung |
|-----------|--------|--------------|
| `auth` | `/` | Login, Registrierung, Logout |
| `dashboard` | `/` | Spielauswahl (Route `/`) |
| `dame` | `/dame` | Dame (Checkers) mit KI und Lobby |
| `hangman` | `/hangman` | Hangman (Galgenmaennchen) |
| `muehle` | `/muehle` | Muehle mit KI und SocketIO-Multiplayer |
| `twentyone` | `/twentyone` | 17 und 4 (Kartenspiel) |
| `backgammon` | `/backgammon` | Backgammon mit KI und Lobby |
| `maumau` | `/maumau` | Mau-Mau mit KI und SocketIO-Multiplayer |
| `pong` | `/pong` | Pong gegen KI (Canvas-basiert, rein clientseitig) |

### Spiellogik-Module (reines Python, kein Flask)

- `dame/checkers_logic.py`, `dame/ai.py`, `dame/game_manager.py`
- `hangman/words.py`
- `muehle/engine/` (board.py, rules.py, ai.py)
- `twentyone/game.py`
- `backgammon/game_logic.py`, `backgammon/ai.py`, `backgammon/game_manager.py`
- `maumau/game_logic.py`, `maumau/ai_player.py`, `maumau/deck.py`

## Konventionen

- Python-Code ohne Type Annotations (Projekt-Stil)
- Templates: Jinja2, deutsche UI-Texte, alle erweitern `templates/base.html`
- CSS: Gemeinsamer Dark Theme in `static/css/common.css` (#1a1a2e Hintergrund, #e94560 Akzent), spielspezifisches CSS in `static/css/<spiel>.css`
- JS: Spielspezifisch in `static/js/<spiel>_game.js`, URL-Prefixe ueber globale Konstanten (GAME_BASE, HANGMAN_BASE, MUEHLE_BASE, TWENTYONE_BASE)
- Konfig via `config.ini` (nicht ueber Env-Vars, ausser SECRET_KEY)
- CSRF-Schutz via Flask-WTF; JS-Requests senden `X-CSRFToken`-Header (Muehle)
- SocketIO-Namespaces `/muehle` und `/maumau` fuer Multiplayer-Events (keine globalen Events)
- Session-Keys sind spielspezifisch prefixed: `hangman_game_id`, `twentyone_sid`

## Bekannte Einschraenkungen

- Kein Datenbank-Migrationstool — Schema-Aenderungen erfordern DB-Neuanlage
- Muehle-KI ist synchron und blockiert den Request (< 2 Sek. bei Tiefe 4)
- Hangman, TwentyOne, Backgammon und Mau-Mau speichern Spielzustand nur im Arbeitsspeicher (verloren bei Server-Neustart)
- Pong laeuft vollstaendig im Browser (kein Server-State)
- Kein Disconnect-Handling im Muehle-Multiplayer
