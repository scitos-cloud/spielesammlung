import uuid
from flask import Blueprint, current_app, jsonify, render_template, session
from flask_login import login_required

from twentyone import twentyone_bp
from twentyone.game import Game

_games: dict[str, Game] = {}


def _get_game() -> Game | None:
    sid = session.get("twentyone_sid")
    if sid:
        return _games.get(sid)
    return None


def _set_game(game: Game) -> None:
    if "twentyone_sid" not in session:
        session["twentyone_sid"] = str(uuid.uuid4())
    _games[session["twentyone_sid"]] = game


@twentyone_bp.route("/")
@login_required
def index():
    return render_template("twentyone/index.html")


@twentyone_bp.route("/api/new", methods=["POST"])
@login_required
def new_game():
    config = current_app.config.get("GAME_CONFIG", {})
    game = Game(config)
    _set_game(game)
    return jsonify(game.to_dict())


@twentyone_bp.route("/api/hit", methods=["POST"])
@login_required
def hit():
    game = _get_game()
    if not game:
        return jsonify({"error": "No active game"}), 400
    return jsonify(game.hit())


@twentyone_bp.route("/api/stand", methods=["POST"])
@login_required
def stand():
    game = _get_game()
    if not game:
        return jsonify({"error": "No active game"}), 400
    return jsonify(game.stand())


@twentyone_bp.route("/api/state", methods=["GET"])
@login_required
def state():
    game = _get_game()
    if not game:
        return jsonify({"error": "No active game"}), 400
    return jsonify(game.to_dict())
