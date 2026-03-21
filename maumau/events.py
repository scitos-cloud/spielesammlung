import time
from datetime import datetime, timezone

from flask import request
from flask_login import current_user
from flask_socketio import emit, join_room

from extensions import socketio, db
from models import MauMauRoom, MauMauGameLog, MauMauGameLogPlayer
from maumau.game_logic import MauMauGame
from maumau.ai_player import AIPlayer
from maumau.deck import SUIT_NAMES, SUIT_SYMBOLS, card_display_value, card_suit, card_value

NS = '/maumau'

# Active games in memory: room_code -> MauMauGame
active_games = {}
# Track which socket_id belongs to which room and user
socket_sessions = {}
# Track waiting room players: room_code -> [{user_id, username, socket_id, is_host}]
waiting_rooms = {}


def format_card(card):
    return card_display_value(card) + SUIT_SYMBOLS.get(card_suit(card), '')


def broadcast_log(room_code, text, entry_type='info'):
    socketio.emit('log_entry', {
        'text': text,
        'time': datetime.now().strftime('%H:%M'),
        'type': entry_type,
    }, to=room_code, namespace=NS)


def format_play_log(player_name, card, result):
    card_str = format_card(card)
    special = result.get('special')
    msg = f"{player_name} spielt {card_str}"
    if special == 'draw2':
        msg += ' \u2192 +2 Karten!'
    elif special == 'skip':
        msg += ' \u2192 Aussetzen!'
    elif special == 'reverse':
        msg += ' \u2192 Richtungswechsel!'
    elif special == 'wish':
        wished_sym = SUIT_SYMBOLS.get(result.get('wished_suit', ''), '')
        msg += f' \u2192 wuenscht {wished_sym}'
    if result.get('mau'):
        msg += ' \u2014 MAU!'
    return msg, ('special' if special else 'play')


def broadcast_game_state(room_code, game):
    for p in game.players:
        if p['type'] == 'human' and p.get('socket_id'):
            state = game.get_state_for_player(p['id'])
            socketio.emit('game_state', state, to=p['socket_id'], namespace=NS)


def run_ai_turn(room_code, app):
    with app.app_context():
        if room_code not in active_games:
            return

        game = active_games[room_code]
        if game.status != 'playing':
            return

        current = game.current_player()
        if current['type'] != 'ai':
            return

        move = AIPlayer.choose_move(game, current)

        if move['action'] == 'play':
            card = move['card']
            wished_suit = move.get('wished_suit')

            socketio.emit('ai_move', {
                'player_name': current['name'],
                'player_id': current['id'],
                'card': card,
                'delay_ms': 800,
            }, to=room_code, namespace=NS)

            time.sleep(0.9)

            result = game.play_card(current['id'], card, wished_suit)

            if result and not result.get('error'):
                log_msg, log_type = format_play_log(current['name'], card, result)
                broadcast_log(room_code, log_msg, log_type)

            if result and result.get('mau_mau'):
                broadcast_game_state(room_code, game)
                handle_game_over(room_code, game, app)
                return

        elif move['action'] == 'draw':
            result = game.draw_card(current['id'])
            n = result.get('draw_count', 1)
            socketio.emit('draw_result', {
                'player_name': current['name'],
                'player_id': current['id'],
                'draw_count': n,
            }, to=room_code, namespace=NS)
            broadcast_log(room_code, f"{current['name']} zieht {n} Karte{'n' if n != 1 else ''}", 'draw')

        broadcast_game_state(room_code, game)

        if game.status == 'playing':
            next_player = game.current_player()
            if next_player['type'] == 'ai':
                schedule_ai_turn(room_code, app, 1.2)


def handle_game_over(room_code, game, app):
    with app.app_context():
        winner_name = 'Unbekannt'
        for p in game.players:
            if str(p['id']) == str(game.winner):
                winner_name = p['name']
                break

        room = MauMauRoom.query.filter_by(room_code=room_code).first()
        if room:
            room.status = 'finished'

        game_log = MauMauGameLog(
            room_id=room_code,
            started_at=room.created_at if room else datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
        )

        winner_user_id = None
        if game.winner and not str(game.winner).startswith('ai_'):
            try:
                winner_user_id = int(game.winner)
            except (ValueError, TypeError):
                pass
        game_log.winner_id = winner_user_id

        game_log.set_game_data({
            'rounds': game.rounds,
            'players': [{'name': p['name'], 'type': p['type']} for p in game.players],
        })

        db.session.add(game_log)
        db.session.flush()

        for idx, p in enumerate(game.players):
            is_winner = str(p['id']) == str(game.winner)
            user_id = None
            if p['type'] == 'human':
                try:
                    user_id = int(p['id'])
                except (ValueError, TypeError):
                    pass

            entry = MauMauGameLogPlayer(
                gamelog_id=game_log.id,
                user_id=user_id,
                player_name=p['name'],
                player_type=p['type'],
                position=idx,
                result='win' if is_winner else 'loss',
            )
            db.session.add(entry)

        db.session.commit()

        broadcast_log(room_code, f"\U0001f3c6 {winner_name} gewinnt! MAU-MAU!", 'winner')
        socketio.emit('game_over', {
            'winner_name': winner_name,
            'winner_id': str(game.winner),
        }, to=room_code, namespace=NS)

        if room_code in active_games:
            del active_games[room_code]
        if room_code in waiting_rooms:
            del waiting_rooms[room_code]


def schedule_ai_turn(room_code, app, delay):
    def runner():
        time.sleep(delay)
        run_ai_turn(room_code, app)
    socketio.start_background_task(runner)


# --- SocketIO Events ---

@socketio.on('join_room', namespace=NS)
def handle_join_room(data):
    room_code = data.get('room_code', '')
    username = data.get('username', '')
    user_id = data.get('user_id', '')

    room = MauMauRoom.query.filter_by(room_code=room_code).first()
    if not room:
        emit('error', {'message': 'Raum nicht gefunden'})
        return

    if room.status != 'waiting':
        emit('error', {'message': 'Spiel laeuft bereits oder ist beendet'})
        return

    join_room(room_code)
    socket_sessions[request.sid] = {'room_code': room_code, 'user_id': user_id, 'username': username}

    if room_code not in waiting_rooms:
        waiting_rooms[room_code] = []

    existing = [p for p in waiting_rooms[room_code] if str(p['user_id']) == str(user_id)]
    if not existing:
        waiting_rooms[room_code].append({
            'user_id': str(user_id),
            'username': username,
            'socket_id': request.sid,
            'is_host': str(room.host_id) == str(user_id),
        })
    else:
        existing[0]['socket_id'] = request.sid

    players_info = [{'name': p['username'], 'is_host': p['is_host']} for p in waiting_rooms[room_code]]
    emit('player_joined', {'players': players_info}, to=room_code)


@socketio.on('start_game', namespace=NS)
def handle_start_game(data):
    room_code = data.get('room_code', '')
    room = MauMauRoom.query.filter_by(room_code=room_code).first()
    if not room:
        emit('error', {'message': 'Raum nicht gefunden'})
        return

    session_info = socket_sessions.get(request.sid, {})
    if str(room.host_id) != str(session_info.get('user_id', '')):
        emit('error', {'message': 'Nur der Host kann das Spiel starten'})
        return

    room.status = 'playing'
    db.session.commit()

    emit('game_started', {'room_code': room_code}, to=room_code)


@socketio.on('join_game', namespace=NS)
def handle_join_game(data):
    from flask import current_app

    room_code = data.get('room_code', '')
    user_id = str(data.get('user_id', ''))
    username = data.get('username', '')

    join_room(room_code)
    socket_sessions[request.sid] = {'room_code': room_code, 'user_id': user_id, 'username': username}

    room = MauMauRoom.query.filter_by(room_code=room_code).first()
    if not room:
        emit('error', {'message': 'Raum nicht gefunden'})
        return

    if room_code not in active_games:
        game = MauMauGame()

        humans_added = set()
        if room_code in waiting_rooms:
            for p in waiting_rooms[room_code]:
                game.add_player(p['user_id'], p['username'], 'human', p['socket_id'])
                humans_added.add(str(p['user_id']))

        if user_id not in humans_added:
            game.add_player(user_id, username, 'human', request.sid)
            humans_added.add(user_id)

        ai_names = ['Bot Alpha', 'Bot Beta', 'Bot Gamma']
        for i in range(room.num_ai_players):
            ai_id = 'ai_' + str(i)
            game.add_player(ai_id, ai_names[i], 'ai')

        if len(game.players) < 2:
            emit('error', {'message': 'Nicht genuegend Spieler'})
            return

        game.start_game()
        active_games[room_code] = game
        broadcast_log(room_code, 'Spiel begonnen', 'info')

        room.status = 'playing'
        db.session.commit()
    else:
        game = active_games[room_code]
        for p in game.players:
            if str(p['id']) == user_id:
                p['socket_id'] = request.sid
                break

    state = game.get_state_for_player(user_id)
    emit('game_state', state)

    broadcast_game_state(room_code, game)

    if game.status == 'playing':
        current = game.current_player()
        if current['type'] == 'ai':
            app = current_app._get_current_object()
            schedule_ai_turn(room_code, app, 0.5)


@socketio.on('play_card', namespace=NS)
def handle_play_card(data):
    from flask import current_app

    session_info = socket_sessions.get(request.sid, {})
    room_code = session_info.get('room_code', '')
    user_id = session_info.get('user_id', '')

    if room_code not in active_games:
        emit('error', {'message': 'Spiel nicht gefunden'})
        return

    game = active_games[room_code]
    card = data.get('card', '')
    wished_suit = data.get('wished_suit')

    result = game.play_card(user_id, card, wished_suit)

    if 'error' in result:
        emit('error', {'message': result['error']})
        return

    broadcast_game_state(room_code, game)

    log_msg, log_type = format_play_log(result['player_name'], card, result)
    broadcast_log(room_code, log_msg, log_type)

    if result.get('mau_mau'):
        app = current_app._get_current_object()
        handle_game_over(room_code, game, app)
        return

    if game.status == 'playing':
        current = game.current_player()
        if current['type'] == 'ai':
            app = current_app._get_current_object()
            schedule_ai_turn(room_code, app, 1.2)


@socketio.on('draw_card', namespace=NS)
def handle_draw_card(data):
    from flask import current_app

    session_info = socket_sessions.get(request.sid, {})
    room_code = session_info.get('room_code', '')
    user_id = session_info.get('user_id', '')

    if room_code not in active_games:
        emit('error', {'message': 'Spiel nicht gefunden'})
        return

    game = active_games[room_code]
    result = game.draw_card(user_id)

    if 'error' in result:
        emit('error', {'message': result['error']})
        return

    emit('draw_result', result)

    n = result['draw_count']
    broadcast_log(room_code, f"{result['player_name']} zieht {n} Karte{'n' if n != 1 else ''}", 'draw')

    broadcast_game_state(room_code, game)

    if game.status == 'playing':
        current = game.current_player()
        if current['type'] == 'ai':
            app = current_app._get_current_object()
            schedule_ai_turn(room_code, app, 1.2)


@socketio.on('disconnect', namespace=NS)
def handle_disconnect():
    session_info = socket_sessions.pop(request.sid, None)
    if not session_info:
        return

    room_code = session_info.get('room_code', '')

    if room_code in waiting_rooms:
        waiting_rooms[room_code] = [p for p in waiting_rooms[room_code] if p['socket_id'] != request.sid]
        if not waiting_rooms[room_code]:
            del waiting_rooms[room_code]

    if room_code in active_games:
        game = active_games[room_code]
        human_connected = False
        for p in game.players:
            if p['type'] == 'human' and p.get('socket_id') and p['socket_id'] != request.sid:
                if p['socket_id'] in socket_sessions:
                    human_connected = True
                    break

        for p in game.players:
            if p.get('socket_id') == request.sid:
                p['socket_id'] = None

        if not human_connected and game.status == 'playing':
            game.status = 'finished'
            room = MauMauRoom.query.filter_by(room_code=room_code).first()
            if room:
                room.status = 'finished'
                db.session.commit()
            del active_games[room_code]
