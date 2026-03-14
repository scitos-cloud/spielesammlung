import json
from datetime import datetime, timezone, timedelta

from flask import render_template, redirect, url_for, request, jsonify, flash
from flask_login import login_required, current_user

from muehle import muehle_bp
from extensions import db
from models import User, MuehleGame, MuehleGameMove
from muehle.engine.board import Board
from muehle.engine.rules import GameState
from muehle.engine.ai import get_ai_move


def _build_state(game):
    board = Board(game.get_board())
    return GameState(
        board=board,
        current_player=game.current_player,
        stones_placed=(game.stones_placed_white, game.stones_placed_black),
        pending_removal=game.pending_removal,
    )


def _save_state(game, state):
    game.set_board(state.board.to_list())
    game.current_player = state.current_player
    game.stones_placed_white = state.stones_placed[0]
    game.stones_placed_black = state.stones_placed[1]
    game.pending_removal = state.pending_removal


def _record_move(game, player, action_dict, board_after):
    move_num = len(game.moves) + 1
    move = MuehleGameMove(
        game_id=game.id,
        move_number=move_num,
        player=player,
        action=action_dict['action'],
        from_pos=action_dict.get('from_pos'),
        to_pos=action_dict.get('to_pos'),
        board_after=json.dumps(board_after),
    )
    db.session.add(move)


@muehle_bp.route('/')
@login_required
def lobby():
    open_games = MuehleGame.query.filter_by(status='waiting', is_vs_computer=False).all()
    my_games = MuehleGame.query.filter(
        ((MuehleGame.white_player_id == current_user.id) | (MuehleGame.black_player_id == current_user.id)),
        MuehleGame.status == 'active'
    ).all()
    threshold = datetime.now(timezone.utc) - timedelta(minutes=5)
    online_users = User.query.filter(User.last_seen >= threshold).order_by(User.username).all()
    return render_template('muehle/lobby.html', open_games=open_games, my_games=my_games,
                           online_users=online_users)


@muehle_bp.route('/game/new', methods=['POST'])
@login_required
def new_game():
    vs_computer = request.form.get('vs_computer') == '1'
    game = MuehleGame(
        white_player_id=current_user.id,
        is_vs_computer=vs_computer,
        status='active' if vs_computer else 'waiting',
    )
    db.session.add(game)
    db.session.commit()
    if vs_computer:
        return redirect(url_for('muehle.play', game_id=game.id))
    flash('Spiel erstellt! Warte auf einen Gegner...')
    return redirect(url_for('muehle.lobby'))


@muehle_bp.route('/game/<int:game_id>')
@login_required
def play(game_id):
    game = MuehleGame.query.get_or_404(game_id)
    if game.status == 'waiting':
        flash('Warte auf einen Gegner...')
        return redirect(url_for('muehle.lobby'))
    if current_user.id == game.white_player_id:
        my_player = 1
    elif current_user.id == game.black_player_id:
        my_player = 2
    else:
        flash('Du bist nicht Teil dieses Spiels.')
        return redirect(url_for('muehle.lobby'))
    return render_template('muehle/board.html', game=game, my_player=my_player)


@muehle_bp.route('/game/<int:game_id>/action', methods=['POST'])
@login_required
def action(game_id):
    game = MuehleGame.query.get_or_404(game_id)
    if game.status != 'active':
        return jsonify({'error': 'Spiel ist nicht aktiv'}), 400

    if current_user.id == game.white_player_id:
        my_player = 1
    elif current_user.id == game.black_player_id:
        my_player = 2
    else:
        return jsonify({'error': 'Nicht dein Spiel'}), 403

    state = _build_state(game)

    if state.current_player != my_player:
        return jsonify({'error': 'Nicht dein Zug'}), 400

    data = request.get_json()
    action_dict = {
        'action': data.get('action'),
        'from_pos': data.get('from_pos'),
        'to_pos': data.get('to_pos'),
    }

    legal = state.legal_actions()
    if not _action_in_list(action_dict, legal):
        return jsonify({'error': 'Ungueltiger Zug', 'legal': legal}), 400

    state, formed_mill = state.apply_action(action_dict)
    _record_move(game, my_player, action_dict, state.board.to_list())
    _save_state(game, state)

    last = action_dict
    response = {'state': _state_to_dict(game, state, last), 'formed_mill': formed_mill}

    winner = state.check_winner()
    if winner:
        game.status = 'finished'
        game.winner = winner
        game.finished_at = datetime.now(timezone.utc)
        db.session.commit()
        response['state'] = _state_to_dict(game, state, last)
        return jsonify(response)

    if game.is_vs_computer and state.current_player == 2 and not state.pending_removal:
        ai_actions = _do_ai_turn(game, state)
        response['ai_actions'] = ai_actions
        state = _build_state(game)
        last_ai = ai_actions[0] if ai_actions else last
        response['state'] = _state_to_dict(game, state, last_ai)
        winner = state.check_winner()
        if winner:
            game.status = 'finished'
            game.winner = winner
            game.finished_at = datetime.now(timezone.utc)

    db.session.commit()
    return jsonify(response)


def _do_ai_turn(game, state):
    actions_taken = []
    ai_action = get_ai_move(state)
    if ai_action is None:
        return actions_taken

    state, formed_mill = state.apply_action(ai_action)
    _record_move(game, 2, ai_action, state.board.to_list())
    _save_state(game, state)
    actions_taken.append(ai_action)

    if formed_mill and state.pending_removal:
        removal = get_ai_move(state)
        if removal:
            state, _ = state.apply_action(removal)
            _record_move(game, 2, removal, state.board.to_list())
            _save_state(game, state)
            actions_taken.append(removal)

    return actions_taken


def _action_in_list(action, legal):
    for la in legal:
        if (la['action'] == action['action']
                and la.get('from_pos') == action.get('from_pos')
                and la.get('to_pos') == action.get('to_pos')):
            return True
    return False


def _state_to_dict(game, state, last_action=None):
    d = {
        'board': state.board.to_list(),
        'current_player': state.current_player,
        'stones_placed_white': state.stones_placed[0],
        'stones_placed_black': state.stones_placed[1],
        'pending_removal': state.pending_removal,
        'status': game.status,
        'winner': game.winner,
    }
    if last_action:
        d['last_action'] = last_action
    return d


@muehle_bp.route('/game/<int:game_id>/join', methods=['POST'])
@login_required
def join_game(game_id):
    game = MuehleGame.query.get_or_404(game_id)
    if game.status != 'waiting':
        flash('Spiel nicht verfuegbar.')
        return redirect(url_for('muehle.lobby'))
    if game.white_player_id == current_user.id:
        flash('Du kannst nicht gegen dich selbst spielen.')
        return redirect(url_for('muehle.lobby'))
    game.black_player_id = current_user.id
    game.status = 'active'
    db.session.commit()
    return redirect(url_for('muehle.play', game_id=game.id))


@muehle_bp.route('/history')
@login_required
def history():
    games = MuehleGame.query.filter(
        ((MuehleGame.white_player_id == current_user.id) | (MuehleGame.black_player_id == current_user.id)),
        MuehleGame.status == 'finished'
    ).order_by(MuehleGame.finished_at.desc()).all()
    return render_template('muehle/history.html', games=games, user=current_user)
