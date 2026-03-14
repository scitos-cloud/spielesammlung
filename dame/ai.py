import random


def evaluate(game):
    """Evaluate board position. Positive = good for white."""
    score = 0
    for r in range(8):
        for c in range(8):
            piece = game.board[r][c]
            if piece == 'w':
                score += 1 + 0.1 * (7 - r)  # closer to promotion = bonus
            elif piece == 'W':
                score += 3 + 0.1 * _center_bonus(r, c)
            elif piece == 'b':
                score -= 1 - 0.1 * r  # closer to promotion = bonus for black
            elif piece == 'B':
                score -= 3 + 0.1 * _center_bonus(r, c)
    return score


def _center_bonus(r, c):
    """Bonus for being near the center."""
    return (3.5 - abs(r - 3.5)) * 0.5 + (3.5 - abs(c - 3.5)) * 0.5


def minimax(game, depth, alpha, beta, maximizing):
    if depth == 0 or game.winner:
        if game.winner == 'w':
            return 100, None
        elif game.winner == 'b':
            return -100, None
        return evaluate(game), None

    color = 'w' if maximizing else 'b'
    all_moves = game.get_all_moves(color)
    if not all_moves:
        return (-100 if maximizing else 100), None

    best_move = None
    moves_list = []
    for (r, c), paths in all_moves.items():
        for path in paths:
            moves_list.append((r, c, path))

    random.shuffle(moves_list)

    if maximizing:
        max_eval = float('-inf')
        for r, c, path in moves_list:
            clone = game.clone()
            clone.make_move(r, c, path)
            eval_score, _ = minimax(clone, depth - 1, alpha, beta, False)
            if eval_score > max_eval:
                max_eval = eval_score
                best_move = (r, c, path)
            alpha = max(alpha, eval_score)
            if beta <= alpha:
                break
        return max_eval, best_move
    else:
        min_eval = float('inf')
        for r, c, path in moves_list:
            clone = game.clone()
            clone.make_move(r, c, path)
            eval_score, _ = minimax(clone, depth - 1, alpha, beta, True)
            if eval_score < min_eval:
                min_eval = eval_score
                best_move = (r, c, path)
            beta = min(beta, eval_score)
            if beta <= alpha:
                break
        return min_eval, best_move


def ai_move(game, depth=4):
    """Compute AI move for black. Returns (from_row, from_col, path) or None."""
    _, best = minimax(game, depth, float('-inf'), float('inf'), False)
    return best
