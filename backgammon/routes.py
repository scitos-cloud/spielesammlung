from datetime import datetime, timezone
from flask import render_template, redirect, url_for, flash, jsonify, request
from flask_login import login_required, current_user
from extensions import db
from models import BackgammonGame as BGGameModel
from backgammon import backgammon_bp
from backgammon import game_manager
from backgammon.ai import get_ai_turn


# --- Lobby ---

@backgammon_bp.route('/')
@login_required
def lobby():
    open_games = BGGameModel.query.filter_by(status='waiting', is_ai_game=False).all()
    my_games = BGGameModel.query.filter(
        ((BGGameModel.white_id == current_user.id) | (BGGameModel.black_id == current_user.id)),
        BGGameModel.status == 'active'
    ).all()
    return render_template('backgammon/lobby.html', open_games=open_games, my_games=my_games)


@backgammon_bp.route('/lobby/start-ai', methods=['POST'])
@login_required
def start_ai():
    game_db = BGGameModel(white_id=current_user.id, black_id=None, is_ai_game=True, status='active')
    db.session.add(game_db)
    db.session.commit()
    game = game_manager.create_game(game_db.id)
    game.roll_dice()
    return jsonify({'status': 'ok', 'game_id': game_db.id})


@backgammon_bp.route('/lobby/create-open', methods=['POST'])
@login_required
def create_open():
    game_db = BGGameModel(white_id=current_user.id, is_ai_game=False, status='waiting')
    db.session.add(game_db)
    db.session.commit()
    flash('Spiel erstellt! Warte auf einen Gegner...')
    return jsonify({'status': 'ok'})


@backgammon_bp.route('/lobby/join/<int:game_id>', methods=['POST'])
@login_required
def join_game(game_id):
    game_db = BGGameModel.query.get_or_404(game_id)
    if game_db.status != 'waiting':
        flash('Spiel nicht verfuegbar.')
        return redirect(url_for('backgammon.lobby'))
    if game_db.white_id == current_user.id:
        flash('Du kannst nicht gegen dich selbst spielen.')
        return redirect(url_for('backgammon.lobby'))
    game_db.black_id = current_user.id
    game_db.status = 'active'
    db.session.commit()
    game = game_manager.create_game(game_db.id)
    game.roll_dice()
    return jsonify({'status': 'ok', 'game_id': game_db.id})


@backgammon_bp.route('/lobby/games')
@login_required
def lobby_games_api():
    open_games = BGGameModel.query.filter_by(status='waiting', is_ai_game=False).all()
    my_games = BGGameModel.query.filter(
        ((BGGameModel.white_id == current_user.id) | (BGGameModel.black_id == current_user.id)),
        BGGameModel.status == 'active'
    ).all()
    return jsonify({
        'open': [{
            'id': g.id,
            'creator': g.white.username,
        } for g in open_games if g.white_id != current_user.id],
        'active': [{
            'id': g.id,
            'opponent': (g.black.username if g.black else 'KI') if g.white_id == current_user.id
                        else g.white.username,
        } for g in my_games],
    })


# --- Rules ---

@backgammon_bp.route('/rules')
@login_required
def rules():
    return render_template('backgammon/rules.html')


# --- Game ---

@backgammon_bp.route('/game/<int:game_id>')
@login_required
def game_page(game_id):
    game_db = BGGameModel.query.get_or_404(game_id)
    if game_db.status == 'waiting':
        flash('Warte auf einen Gegner...')
        return redirect(url_for('backgammon.lobby'))
    if current_user.id == game_db.white_id:
        my_player = 1
    elif current_user.id == game_db.black_id:
        my_player = 2
    elif game_db.is_ai_game and current_user.id == game_db.white_id:
        my_player = 1
    else:
        flash('Du bist nicht Teil dieses Spiels.')
        return redirect(url_for('backgammon.lobby'))
    opponent = 'KI' if game_db.is_ai_game else (
        game_db.black.username if my_player == 1 else game_db.white.username
    )
    return render_template('backgammon/game.html', game_id=game_id, my_player=my_player,
                           is_ai=game_db.is_ai_game, opponent=opponent)


@backgammon_bp.route('/game/<int:game_id>/state')
@login_required
def game_state(game_id):
    game_db = BGGameModel.query.get_or_404(game_id)
    game = game_manager.get_game(game_id)
    if game is None:
        if game_db.status == 'finished':
            return jsonify({
                'board': [0] * 24, 'bar': [0, 0], 'off': [15, 15],
                'current_player': 0, 'dice': [], 'dice_rolled': [],
                'winner': 1 if game_db.result == 'white' else 2,
                'legal_moves': [], 'status': 'finished',
            })
        game = game_manager.create_game(game_id)
        game.roll_dice()

    # Auto-roll if no dice and game not over
    if not game.dice and not game.winner:
        game.roll_dice()
        # If no legal moves, skip turn
        if not game.all_legal_moves():
            game.end_turn()
            game.roll_dice()

    state = game.to_dict()
    state['status'] = 'finished' if game.winner else 'playing'
    return jsonify(state)


@backgammon_bp.route('/game/<int:game_id>/move', methods=['POST'])
@login_required
def make_move(game_id):
    game_db = BGGameModel.query.get_or_404(game_id)
    game = game_manager.get_game(game_id)
    if game is None or game.winner:
        return jsonify({'error': 'Spiel nicht aktiv'}), 400

    if current_user.id == game_db.white_id:
        my_player = 1
    elif current_user.id == game_db.black_id:
        my_player = 2
    else:
        return jsonify({'error': 'Nicht dein Spiel'}), 403

    if game.current_player != my_player:
        return jsonify({'error': 'Nicht dein Zug'}), 400

    data = request.get_json()
    fr = data.get('from')
    to = data.get('to')
    die = data.get('die')

    # Validate move is legal
    legal = game.valid_moves()
    if not any(m[0] == fr and m[1] == to and m[2] == die for m in legal):
        return jsonify({'error': 'Ungueltiger Zug', 'legal': legal}), 400

    game.apply_move(fr, to, die)

    ai_moves = None

    # Check if turn is over
    if not game.winner and (not game.dice or not game.all_legal_moves()):
        game.end_turn()

        # AI turn
        if game_db.is_ai_game and not game.winner and game.current_player == 2:
            ai_moves = _play_ai(game, game_db)

    # Check for winner
    if game.winner:
        _finish_game(game_db, game)

    state = game.to_dict()
    state['status'] = 'finished' if game.winner else 'playing'
    result = {'state': state}
    if ai_moves is not None:
        result['ai_moves'] = [{'from': m[0], 'to': m[1], 'die': m[2]} for m in ai_moves]
    return jsonify(result)


def _play_ai(game, game_db):
    """Play one AI turn. Returns list of moves."""
    game.roll_dice()
    if not game.all_legal_moves():
        game.end_turn()
        game.roll_dice()
        return []

    moves = get_ai_turn(game)
    # End AI turn
    if not game.winner:
        game.end_turn()
        # Roll for next human turn
        game.roll_dice()
        if not game.all_legal_moves():
            game.end_turn()
            game.roll_dice()
    return moves


def _finish_game(game_db, game):
    game_db.status = 'finished'
    if game.winner == 1:
        game_db.result = 'white'
        game_db.winner_id = game_db.white_id
    else:
        game_db.result = 'black'
        game_db.winner_id = game_db.black_id if game_db.black_id else None
    game_db.finished_at = datetime.now(timezone.utc)
    db.session.commit()
    game_manager.remove_game(game_db.id)
