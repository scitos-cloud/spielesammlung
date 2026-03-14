import random

from muehle.engine.rules import GameState


def evaluate(state: GameState) -> float:
    """Heuristic evaluation from player 1's perspective."""
    winner = state.check_winner()
    if winner == 1:
        return 10000
    if winner == 2:
        return -10000

    board = state.board
    w_stones = board.count_stones(1)
    b_stones = board.count_stones(2)

    # Stone advantage
    score = (w_stones - b_stones) * 100

    # Mill count
    from muehle.engine.board import MILLS
    for mill in MILLS:
        vals = [board[p] for p in mill]
        if vals.count(1) == 3:
            score += 50
        elif vals.count(2) == 3:
            score -= 50
        # Potential mills (2 stones + 1 empty)
        elif vals.count(1) == 2 and vals.count(0) == 1:
            score += 10
        elif vals.count(2) == 2 and vals.count(0) == 1:
            score -= 10

    # Flying phase bonus
    if state.stones_placed[0] >= 9 and w_stones == 3:
        score += 30
    if state.stones_placed[1] >= 9 and b_stones == 3:
        score -= 30

    return score


def minimax(state: GameState, depth: int, alpha: float, beta: float,
            maximizing: bool) -> tuple:
    """Minimax with alpha-beta pruning. Returns (score, action)."""
    winner = state.check_winner()
    if winner is not None or depth == 0:
        return evaluate(state), None

    actions = state.legal_actions()
    if not actions:
        return evaluate(state), None

    best_action = actions[0]

    if maximizing:
        max_eval = float('-inf')
        for action in actions:
            new_state, _ = state.apply_action(action)
            # After a mill, same player removes — still maximizing if player 1
            next_max = new_state.current_player == 1
            val, _ = minimax(new_state, depth - 1, alpha, beta, next_max)
            if val > max_eval:
                max_eval = val
                best_action = action
            alpha = max(alpha, val)
            if beta <= alpha:
                break
        return max_eval, best_action
    else:
        min_eval = float('inf')
        for action in actions:
            new_state, _ = state.apply_action(action)
            next_max = new_state.current_player == 1
            val, _ = minimax(new_state, depth - 1, alpha, beta, next_max)
            if val < min_eval:
                min_eval = val
                best_action = action
            beta = min(beta, val)
            if beta <= alpha:
                break
        return min_eval, best_action


def get_ai_move(state: GameState, depth: int = 4) -> dict:
    """Get best move for the current player (AI plays as player 2)."""
    maximizing = state.current_player == 1
    _, action = minimax(state, depth, float('-inf'), float('inf'), maximizing)
    return action
