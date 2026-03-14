from datetime import datetime, timezone
from flask import render_template, redirect, url_for, flash, jsonify, request
from flask_login import login_required, current_user
from extensions import db
from models import User, DameGame
from dame import dame_bp
from dame import game_manager
from dame.ai import ai_move


# --- Lobby ---

@dame_bp.route('/lobby')
@login_required
def lobby():
    return render_template('dame/lobby.html')


@dame_bp.route('/lobby/players')
@login_required
def lobby_players():
    players = game_manager.get_lobby_players()
    result = [{'id': uid, 'username': info['username']}
              for uid, info in players.items() if uid != current_user.id]
    return jsonify(result)


@dame_bp.route('/lobby/users')
@login_required
def all_users():
    users = User.query.filter(User.id != current_user.id).order_by(User.username).all()
    lobby_ids = set(game_manager.lobby_players.keys())
    result = []
    for u in users:
        games = DameGame.query.filter(
            db.or_(DameGame.white_id == u.id, DameGame.black_id == u.id),
            DameGame.finished_at.isnot(None)
        ).count()
        wins = DameGame.query.filter(DameGame.winner_id == u.id, DameGame.finished_at.isnot(None)).count()
        result.append({
            'id': u.id,
            'username': u.username,
            'in_lobby': u.id in lobby_ids,
            'games': games,
            'wins': wins,
        })
    return jsonify(result)


@dame_bp.route('/lobby/join', methods=['POST'])
@login_required
def join_lobby():
    game_manager.join_lobby(current_user.id, current_user.username)
    return jsonify({'status': 'ok'})


@dame_bp.route('/lobby/leave', methods=['POST'])
@login_required
def leave_lobby():
    game_manager.leave_lobby(current_user.id)
    return jsonify({'status': 'ok'})


@dame_bp.route('/lobby/challenge/<int:user_id>', methods=['POST'])
@login_required
def challenge(user_id):
    if user_id == current_user.id:
        return jsonify({'error': 'Kann dich nicht selbst herausfordern'}), 400
    if user_id not in game_manager.lobby_players:
        return jsonify({'error': 'Spieler nicht in Lobby'}), 400
    cid = game_manager.create_challenge(current_user.id, current_user.username, user_id)
    return jsonify({'status': 'ok', 'challenge_id': cid})


@dame_bp.route('/lobby/check')
@login_required
def check_challenges():
    challenges = game_manager.get_challenges_for_user(current_user.id)
    result = [{'id': cid, 'challenger_name': ch['challenger_name']}
              for cid, ch in challenges.items()]
    return jsonify(result)


@dame_bp.route('/lobby/accept/<int:challenge_id>', methods=['POST'])
@login_required
def accept_challenge(challenge_id):
    result = game_manager.accept_challenge(challenge_id)
    if result is None:
        return jsonify({'error': 'Herausforderung nicht gefunden'}), 404
    white_id, black_id = result
    game_db = DameGame(white_id=white_id, black_id=black_id, is_ai_game=False)
    db.session.add(game_db)
    db.session.commit()
    game_manager.create_game(game_db.id)
    game_manager.leave_lobby(white_id)
    game_manager.leave_lobby(black_id)
    return jsonify({'status': 'ok', 'game_id': game_db.id})


@dame_bp.route('/lobby/decline/<int:challenge_id>', methods=['POST'])
@login_required
def decline_challenge(challenge_id):
    game_manager.decline_challenge(challenge_id)
    return jsonify({'status': 'ok'})


@dame_bp.route('/lobby/start-ai', methods=['POST'])
@login_required
def start_ai():
    game_db = DameGame(white_id=current_user.id, black_id=None, is_ai_game=True)
    db.session.add(game_db)
    db.session.commit()
    game_manager.create_game(game_db.id)
    game_manager.leave_lobby(current_user.id)
    return jsonify({'status': 'ok', 'game_id': game_db.id})


# --- Game ---

def _player_color(game_db, user_id):
    if game_db.white_id == user_id:
        return 'w'
    if game_db.black_id == user_id:
        return 'b'
    return None


@dame_bp.route('/game/<int:game_id>')
@login_required
def game_page(game_id):
    game_db = DameGame.query.get_or_404(game_id)
    color = _player_color(game_db, current_user.id)
    if color is None and not game_db.is_ai_game:
        return "Nicht dein Spiel", 403
    return render_template('dame/game.html', game_id=game_id, color=color or 'w',
                           is_ai=game_db.is_ai_game,
                           opponent=game_db.black.username if game_db.black else 'KI')


@dame_bp.route('/game/<int:game_id>/state')
@login_required
def game_state(game_id):
    game = game_manager.get_game(game_id)
    if game is None:
        game_db = DameGame.query.get_or_404(game_id)
        return jsonify({'finished': True, 'result': game_db.result, 'winner': game_db.result})
    state = game.to_dict()
    game_db = db.session.get(DameGame, game_id)
    color = _player_color(game_db, current_user.id)
    valid_moves = {}
    if color == game.turn and not game.winner:
        all_moves = game.get_all_moves(color)
        for (r, c), paths in all_moves.items():
            valid_moves[f"{r},{c}"] = [list(map(list, path)) for path in paths]
    state['valid_moves'] = valid_moves
    state['finished'] = game.winner is not None
    state['move_log'] = game_manager.get_move_log(game_id)
    return jsonify(state)


@dame_bp.route('/game/<int:game_id>/move', methods=['POST'])
@login_required
def make_move(game_id):
    game = game_manager.get_game(game_id)
    if game is None:
        return jsonify({'error': 'Spiel nicht gefunden'}), 404
    game_db = db.session.get(DameGame, game_id)
    color = _player_color(game_db, current_user.id)
    if color != game.turn:
        return jsonify({'error': 'Nicht dein Zug'}), 400

    data = request.get_json()
    from_row = data.get('from_row')
    from_col = data.get('from_col')
    path = data.get('path')

    if from_row is None or from_col is None or not path:
        return jsonify({'error': 'Ungueltiger Zug'}), 400

    path_tuples = [tuple(p) for p in path]
    is_capture = abs(path_tuples[0][0] - from_row) == 2
    if not game.make_move(from_row, from_col, path_tuples):
        return jsonify({'error': 'Ungueltiger Zug'}), 400

    game_manager.add_move_log(game_id, color, (from_row, from_col), path_tuples, is_capture)
    last_move = {'from': [from_row, from_col], 'to': list(path_tuples[-1]), 'player': color}

    if game.winner:
        _finish_game(game_db, game)
        state = game.to_dict()
        state['finished'] = True
        state['last_move'] = last_move
        state['move_log'] = game_manager.get_move_log(game_id)
        return jsonify(state)

    ai_last_move = None
    if game_db.is_ai_game and game.turn == 'b':
        result = ai_move(game)
        if result:
            r, c, ai_path = result
            ai_is_capture = abs(ai_path[0][0] - r) == 2
            game.make_move(r, c, ai_path)
            game_manager.add_move_log(game_id, 'b', (r, c), ai_path, ai_is_capture)
            ai_last_move = {'from': [r, c], 'to': list(ai_path[-1]), 'player': 'b'}
        if game.winner:
            _finish_game(game_db, game)

    state = game.to_dict()
    state['finished'] = game.winner is not None
    state['last_move'] = ai_last_move or last_move
    state['move_log'] = game_manager.get_move_log(game_id)
    return jsonify(state)


@dame_bp.route('/game/<int:game_id>/resign', methods=['POST'])
@login_required
def resign(game_id):
    game = game_manager.get_game(game_id)
    if game is None:
        return jsonify({'error': 'Spiel nicht gefunden'}), 404
    game_db = db.session.get(DameGame, game_id)
    color = _player_color(game_db, current_user.id)
    if color is None:
        return jsonify({'error': 'Nicht dein Spiel'}), 403
    game.winner = 'b' if color == 'w' else 'w'
    _finish_game(game_db, game)
    return jsonify({'status': 'ok', 'winner': game.winner})


def _finish_game(game_db, game):
    game_db.result = game.winner
    game_db.finished_at = datetime.now(timezone.utc)
    if game.winner == 'w':
        game_db.winner_id = game_db.white_id
    elif game.winner == 'b':
        game_db.winner_id = game_db.black_id
    db.session.commit()
    game_manager.remove_game(game_db.id)


# --- Profile ---

@dame_bp.route('/profile/<int:user_id>')
@login_required
def profile(user_id):
    user = User.query.get_or_404(user_id)

    finished_games = DameGame.query.filter(
        db.or_(DameGame.white_id == user_id, DameGame.black_id == user_id),
        DameGame.finished_at.isnot(None)
    ).order_by(DameGame.finished_at.desc()).all()

    active_games = DameGame.query.filter(
        db.or_(DameGame.white_id == user_id, DameGame.black_id == user_id),
        DameGame.finished_at.is_(None)
    ).order_by(DameGame.started_at.desc()).all()

    wins = sum(1 for g in finished_games if g.winner_id == user_id)
    losses = sum(1 for g in finished_games if g.winner_id and g.winner_id != user_id)
    draws = sum(1 for g in finished_games if g.result == 'draw')
    total = len(finished_games)
    win_rate = round(wins / total * 100) if total > 0 else 0

    history = []
    for g in finished_games:
        if g.white_id == user_id:
            opponent = g.black.username if g.black else 'KI'
            color = 'Weiss'
        else:
            opponent = g.white.username
            color = 'Schwarz'

        if g.result == 'draw':
            result_text = 'Unentschieden'
            result_class = 'draw'
        elif g.winner_id == user_id:
            result_text = 'Sieg'
            result_class = 'win'
        else:
            result_text = 'Niederlage'
            result_class = 'loss'

        game_type = 'KI' if g.is_ai_game else 'PvP'

        history.append({
            'id': g.id,
            'opponent': opponent,
            'color': color,
            'result': result_text,
            'result_class': result_class,
            'game_type': game_type,
            'date': g.finished_at.strftime('%d.%m.%Y %H:%M') if g.finished_at else '',
        })

    active = []
    for g in active_games:
        if g.white_id == user_id:
            opponent = g.black.username if g.black else 'KI'
        else:
            opponent = g.white.username
        active.append({
            'id': g.id,
            'opponent': opponent,
            'game_type': 'KI' if g.is_ai_game else 'PvP',
            'started': g.started_at.strftime('%d.%m.%Y %H:%M') if g.started_at else '',
        })

    return render_template('dame/profile.html', user=user, wins=wins, losses=losses,
                           draws=draws, total=total, win_rate=win_rate,
                           history=history, active=active)
