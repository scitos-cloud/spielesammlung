import json
from datetime import datetime, timezone

from flask_login import current_user
from flask_socketio import emit, join_room

from extensions import socketio, db
from models import MuehleGame, MuehleGameMove
from muehle.engine.board import Board
from muehle.engine.rules import GameState


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


def _action_in_list(action, legal):
    for la in legal:
        if (la['action'] == action['action']
                and la.get('from_pos') == action.get('from_pos')
                and la.get('to_pos') == action.get('to_pos')):
            return True
    return False


@socketio.on('join_game', namespace='/muehle')
def on_join(data):
    if not current_user.is_authenticated:
        return
    game_id = data.get('game_id')
    join_room(f'game_{game_id}')
    game = MuehleGame.query.get(game_id)
    if game:
        state = _build_state(game)
        emit('state_update', {
            'board': state.board.to_list(),
            'current_player': state.current_player,
            'stones_placed_white': state.stones_placed[0],
            'stones_placed_black': state.stones_placed[1],
            'pending_removal': state.pending_removal,
            'status': game.status,
            'winner': game.winner,
        })


@socketio.on('player_action', namespace='/muehle')
def on_action(data):
    if not current_user.is_authenticated:
        return

    game_id = data.get('game_id')
    game = MuehleGame.query.get(game_id)
    if not game or game.status != 'active':
        emit('error', {'message': 'Spiel nicht aktiv'})
        return

    if current_user.id == game.white_player_id:
        my_player = 1
    elif current_user.id == game.black_player_id:
        my_player = 2
    else:
        emit('error', {'message': 'Nicht dein Spiel'})
        return

    state = _build_state(game)
    if state.current_player != my_player:
        emit('error', {'message': 'Nicht dein Zug'})
        return

    action_dict = {
        'action': data.get('action'),
        'from_pos': data.get('from_pos'),
        'to_pos': data.get('to_pos'),
    }

    legal = state.legal_actions()
    if not _action_in_list(action_dict, legal):
        emit('error', {'message': 'Ungueltiger Zug'})
        return

    state, formed_mill = state.apply_action(action_dict)
    _record_move(game, my_player, action_dict, state.board.to_list())
    _save_state(game, state)

    winner = state.check_winner()
    if winner:
        game.status = 'finished'
        game.winner = winner
        game.finished_at = datetime.now(timezone.utc)

    db.session.commit()

    room = f'game_{game_id}'
    emit('state_update', {
        'board': state.board.to_list(),
        'current_player': state.current_player,
        'stones_placed_white': state.stones_placed[0],
        'stones_placed_black': state.stones_placed[1],
        'pending_removal': state.pending_removal,
        'status': game.status,
        'winner': game.winner,
        'last_action': action_dict,
        'formed_mill': formed_mill,
    }, room=room)
