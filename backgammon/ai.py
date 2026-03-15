"""
Backgammon AI — simple positional evaluation with full-turn search.

The AI always plays as player 2 (black).
"""

import random


def get_ai_turn(game):
    """
    Play a complete AI turn on *game* (mutates it in place).

    Assumes dice are already rolled on game.

    Steps:
        1. Generate all maximal turns.
        2. Evaluate each resulting position; pick the best.
        3. Apply the chosen moves to the real game.

    Returns:
        list of (from, to, die) moves actually played (empty if stuck).
    """
    turns = game.generate_turns()

    # No moves possible (single empty tuple sentinel)
    if turns == [()]:
        return []

    # If the search space is huge, sample randomly
    if len(turns) > 2000:
        turns = random.sample(turns, 500)

    best_score = None
    best_turn = ()

    for turn in turns:
        g = game.clone()
        for move in turn:
            g.apply_move(move[0], move[1], move[2])
        score = _evaluate(g)
        if best_score is None or score > best_score:
            best_score = score
            best_turn = turn

    # Apply the chosen moves to the actual game
    chosen = list(best_turn)
    for move in chosen:
        game.apply_move(move[0], move[1], move[2])

    return chosen


# ------------------------------------------------------------------
# Position evaluation (from black / player-2 perspective)
# ------------------------------------------------------------------

def _evaluate(game):
    """
    Heuristic evaluation of a board position for player 2 (black).

    Components:
        +50  per black checker borne off
        -50  per white checker borne off
        -40  per black checker on bar
        +30  per white checker on bar
         +8  per "made point" (2+ black checkers on a point)
         +5  extra for anchors in white's home board (idx 0-5)
        -15  per blot (single black checker exposed)
         -0.5 per pip (total distance for black to bear off)
    """
    score = 0.0

    # Borne off
    score += 50 * game.off[1]   # black off
    score -= 50 * game.off[0]   # white off

    # Bar
    score -= 40 * game.bar[1]   # black on bar
    score += 30 * game.bar[0]   # white on bar

    # Pip count for black (checkers on bar count as 25 pips away)
    pip = 25 * game.bar[1]

    for i in range(24):
        v = game.board[i]
        if v < 0:
            # Black checkers
            count = -v
            dist = 24 - i  # distance to bear off for black
            pip += dist * count

            if count >= 2:
                score += 8
                # Anchor bonus in white's home (idx 0-5)
                if i <= 5:
                    score += 5
            elif count == 1:
                score -= 15  # blot
        elif v > 0:
            # White checkers — no direct scoring beyond what's above
            pass

    score -= 0.5 * pip

    return score
