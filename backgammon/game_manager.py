from backgammon.game_logic import BackgammonGame

# Active games: {game_id: BackgammonGame}
active_games = {}


def create_game(game_id):
    game = BackgammonGame()
    active_games[game_id] = game
    return game


def get_game(game_id):
    return active_games.get(game_id)


def remove_game(game_id):
    active_games.pop(game_id, None)
