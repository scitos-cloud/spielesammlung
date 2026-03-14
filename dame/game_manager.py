import time
from dame.checkers_logic import CheckersGame

# Active games: {game_id: CheckersGame}
active_games = {}

# Move logs: {game_id: [{'nr': int, 'player': str, 'from': str, 'to': str, 'capture': bool}]}
move_logs = {}

# Lobby: {user_id: {'username': str, 'timestamp': float}}
lobby_players = {}

# Pending challenges: {game_id: {'challenger_id': int, 'challenged_id': int, 'challenger_name': str}}
pending_challenges = {}

_challenge_counter = 0


def join_lobby(user_id, username):
    lobby_players[user_id] = {'username': username, 'timestamp': time.time()}


def leave_lobby(user_id):
    lobby_players.pop(user_id, None)


def get_lobby_players():
    return {uid: info for uid, info in lobby_players.items()}


def create_challenge(challenger_id, challenger_name, challenged_id):
    global _challenge_counter
    _challenge_counter += 1
    challenge_id = _challenge_counter
    pending_challenges[challenge_id] = {
        'challenger_id': challenger_id,
        'challenged_id': challenged_id,
        'challenger_name': challenger_name,
    }
    return challenge_id


def get_challenges_for_user(user_id):
    return {cid: ch for cid, ch in pending_challenges.items()
            if ch['challenged_id'] == user_id}


def accept_challenge(challenge_id):
    """Accept a challenge. Returns (game_db_id_placeholder, CheckersGame) or None."""
    ch = pending_challenges.pop(challenge_id, None)
    if ch is None:
        return None
    return ch['challenger_id'], ch['challenged_id']


def decline_challenge(challenge_id):
    pending_challenges.pop(challenge_id, None)


def create_game(game_id):
    """Create a new active game with given DB game ID."""
    game = CheckersGame()
    active_games[game_id] = game
    move_logs[game_id] = []
    return game


def add_move_log(game_id, player, from_pos, path, is_capture):
    """Add a move entry to the log."""
    log = move_logs.get(game_id, [])
    nr = len(log) + 1
    from_str = pos_to_notation(from_pos[0], from_pos[1])
    to_str = pos_to_notation(path[-1][0], path[-1][1])
    if len(path) > 1:
        via = [pos_to_notation(p[0], p[1]) for p in path]
        to_str = '-'.join(via)
    sep = 'x' if is_capture else '-'
    log.append({
        'nr': nr,
        'player': player,
        'notation': f"{from_str}{sep}{to_str}",
    })
    move_logs[game_id] = log


def get_move_log(game_id):
    return move_logs.get(game_id, [])


def pos_to_notation(row, col):
    """Convert (row, col) to chess-like notation: a-h columns, 8-1 rows."""
    return chr(ord('a') + col) + str(8 - row)


def get_game(game_id):
    return active_games.get(game_id)


def remove_game(game_id):
    active_games.pop(game_id, None)
    # Keep move_logs so finished game page can still show the log
