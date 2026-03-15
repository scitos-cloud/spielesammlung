"""
Backgammon game logic — pure Python, no framework dependencies.

Board conventions:
    - board[0..23] corresponds to points 1..24.
    - Positive values = white (player 1) checkers.
    - Negative values = black (player 2) checkers.
    - White moves high→low (24→1), black moves low→high (1→24).
    - bar = [white_on_bar, black_on_bar]
    - off = [white_borne_off, black_borne_off]
    - current_player: 1 (white) or 2 (black)
"""

import copy
import random


class BackgammonGame:
    """Full-rules Backgammon game state and logic."""

    def __init__(self):
        self.board = [0] * 24
        self.bar = [0, 0]      # [white, black]
        self.off = [0, 0]      # [white, black]
        self.current_player = 1
        self.dice = []
        self.dice_rolled = []
        self.winner = None
        self._setup_initial()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_initial(self):
        """Standard backgammon starting position."""
        self.board = [0] * 24
        # Point 1 (idx 0): 2 black
        self.board[0] = -2
        # Point 6 (idx 5): 5 white
        self.board[5] = 5
        # Point 8 (idx 7): 3 white
        self.board[7] = 3
        # Point 12 (idx 11): 5 black
        self.board[11] = -5
        # Point 13 (idx 12): 5 white
        self.board[12] = 5
        # Point 17 (idx 16): 3 black
        self.board[16] = -3
        # Point 19 (idx 18): 5 black
        self.board[18] = -5
        # Point 24 (idx 23): 2 white
        self.board[23] = 2

    # ------------------------------------------------------------------
    # Cloning
    # ------------------------------------------------------------------

    def clone(self):
        """Return an independent deep copy of this game state."""
        g = BackgammonGame.__new__(BackgammonGame)
        g.board = self.board[:]
        g.bar = self.bar[:]
        g.off = self.off[:]
        g.current_player = self.current_player
        g.dice = self.dice[:]
        g.dice_rolled = self.dice_rolled[:]
        g.winner = self.winner
        return g

    # ------------------------------------------------------------------
    # Dice
    # ------------------------------------------------------------------

    def roll_dice(self):
        """Roll two six-sided dice.  Doubles yield four dice."""
        d1 = random.randint(1, 6)
        d2 = random.randint(1, 6)
        self.dice_rolled = [d1, d2]
        if d1 == d2:
            self.dice = [d1] * 4
        else:
            self.dice = [d1, d2]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _player_sign(self, player=None):
        """Return +1 for white (player 1), -1 for black (player 2)."""
        p = player if player is not None else self.current_player
        return 1 if p == 1 else -1

    def _bar_index(self, player=None):
        """Index into self.bar / self.off for the given player."""
        p = player if player is not None else self.current_player
        return 0 if p == 1 else 1

    def _is_own(self, idx, player=None):
        sign = self._player_sign(player)
        return (self.board[idx] > 0) if sign == 1 else (self.board[idx] < 0)

    def _own_count(self, idx, player=None):
        sign = self._player_sign(player)
        v = self.board[idx]
        if sign == 1:
            return v if v > 0 else 0
        else:
            return -v if v < 0 else 0

    def _opponent_count(self, idx, player=None):
        sign = self._player_sign(player)
        v = self.board[idx]
        if sign == 1:
            return -v if v < 0 else 0
        else:
            return v if v > 0 else 0

    def _can_land(self, idx, player=None):
        """Can the current player land on board[idx]?"""
        return self._opponent_count(idx, player) < 2

    def _all_in_home(self, player=None):
        """Are all of the player's checkers in their home board (or borne off)?"""
        p = player if player is not None else self.current_player
        bi = self._bar_index(p)
        if self.bar[bi] > 0:
            return False
        sign = self._player_sign(p)
        if p == 1:
            # White home: idx 0-5
            for i in range(6, 24):
                if sign == 1 and self.board[i] > 0:
                    return False
        else:
            # Black home: idx 18-23
            for i in range(0, 18):
                if sign == -1 and self.board[i] < 0:
                    return False
        return True

    def _farthest_from_off(self, player=None):
        """
        Index of the farthest occupied point from bearing-off edge.
        For white (home 0-5) that is the highest occupied idx in 0-5.
        For black (home 18-23) that is the lowest occupied idx in 18-23.
        Returns None if no checkers in home.
        """
        p = player if player is not None else self.current_player
        sign = self._player_sign(p)
        if p == 1:
            for i in range(5, -1, -1):
                if sign == 1 and self.board[i] > 0:
                    return i
        else:
            for i in range(18, 24):
                if sign == -1 and self.board[i] < 0:
                    return i
        return None

    # ------------------------------------------------------------------
    # Move generation for a single die
    # ------------------------------------------------------------------

    def moves_for_die(self, die):
        """
        Return list of (from, to, die) tuples for the given die value.
        from = -1 means entering from bar.
        to   = -2 means bearing off.
        """
        moves = []
        p = self.current_player
        bi = self._bar_index()
        sign = self._player_sign()

        # --- Must enter from bar first ---
        if self.bar[bi] > 0:
            if p == 1:
                target = 24 - die  # white enters high end
            else:
                target = die - 1   # black enters low end
            if 0 <= target <= 23 and self._can_land(target):
                moves.append((-1, target, die))
            return moves  # no other moves allowed while on bar

        # --- Normal moves and bearing off ---
        all_home = self._all_in_home()

        for i in range(24):
            if not self._is_own(i):
                continue

            if p == 1:
                target = i - die  # white moves toward 0
            else:
                target = i + die  # black moves toward 23

            # Bearing off
            if p == 1 and target < 0:
                if all_home:
                    if target == -1:
                        # Exact bear-off (landing on -1 means exactly off)
                        # Actually target < 0 means die >= i+1.
                        # Exact: die == i + 1  →  target == -1
                        pass  # check below
                    # Exact: die == i+1
                    if die == i + 1:
                        moves.append((i, -2, die))
                    elif die > i + 1:
                        # Over-bear: allowed only from farthest point
                        farthest = self._farthest_from_off()
                        if farthest is not None and i == farthest:
                            moves.append((i, -2, die))
                continue
            if p == 2 and target > 23:
                if all_home:
                    dist = 24 - i  # distance for black at idx i
                    if die == dist:
                        moves.append((i, -2, die))
                    elif die > dist:
                        farthest = self._farthest_from_off()
                        if farthest is not None and i == farthest:
                            moves.append((i, -2, die))
                continue

            # Normal move
            if 0 <= target <= 23 and self._can_land(target):
                moves.append((i, target, die))

        return moves

    # ------------------------------------------------------------------
    # All legal moves (union over remaining dice)
    # ------------------------------------------------------------------

    def all_legal_moves(self):
        """Union of moves_for_die for each unique remaining die value."""
        seen = set()
        moves = []
        for d in set(self.dice):
            for m in self.moves_for_die(d):
                if m not in seen:
                    seen.add(m)
                    moves.append(m)
        return moves

    # ------------------------------------------------------------------
    # Apply a single move
    # ------------------------------------------------------------------

    def apply_move(self, fr, to, die):
        """
        Execute one move. Removes the used die from self.dice.
        Checks for win (15 borne off).
        """
        sign = self._player_sign()
        bi = self._bar_index()
        opp_bi = 1 - bi

        # Remove die
        self.dice.remove(die)

        # --- From ---
        if fr == -1:
            # From bar
            self.bar[bi] -= 1
        else:
            self.board[fr] -= sign

        # --- To ---
        if to == -2:
            # Bear off
            self.off[bi] += 1
        else:
            # Hit opponent blot?
            if self._opponent_count(to) == 1:
                self.board[to] = 0
                self.bar[opp_bi] += 1
            self.board[to] += sign

        # Check win
        if self.off[bi] == 15:
            self.winner = self.current_player

    # ------------------------------------------------------------------
    # End turn
    # ------------------------------------------------------------------

    def end_turn(self):
        """Switch to the other player, clear dice."""
        self.current_player = 2 if self.current_player == 1 else 1
        self.dice = []
        self.dice_rolled = []

    # ------------------------------------------------------------------
    # Generate all maximal turns
    # ------------------------------------------------------------------

    def generate_turns(self, _limit=5000):
        """
        Generate all maximal-length turns (sequences of moves using the
        most dice possible).  Returns a list of move-lists, where each
        move is (from, to, die).

        Rules enforced:
          - Must use as many dice as possible.
          - If only one of two unequal dice can be used, must use the
            higher one.
          - Deduplicated by (from, to) sequence.
        """
        results = []
        self._gen_turns_recursive([], results, _limit)

        if not results:
            return [()]

        # Filter to maximum length
        max_len = max(len(t) for t in results)
        maximal = [t for t in results if len(t) == max_len]

        # If max_len == 1 and we have two different dice, keep only moves
        # using the higher die (if any exist).
        if max_len == 1 and len(self.dice_rolled) == 2 and self.dice_rolled[0] != self.dice_rolled[1]:
            higher = max(self.dice_rolled)
            higher_turns = [t for t in maximal if t[0][2] == higher]
            if higher_turns:
                maximal = higher_turns

        # Deduplicate by (from, to) tuples
        seen = set()
        deduped = []
        for turn in maximal:
            key = tuple((m[0], m[1]) for m in turn)
            if key not in seen:
                seen.add(key)
                deduped.append(turn)

        return deduped

    def _gen_turns_recursive(self, path, results, limit):
        """Recursive helper for generate_turns."""
        if len(results) >= limit:
            return

        found_move = False
        tried_dice = set()

        for idx, die in enumerate(self.dice):
            if die in tried_dice:
                continue
            tried_dice.add(die)

            legal = self.moves_for_die(die)
            for move in legal:
                found_move = True
                if len(results) >= limit:
                    return
                g = self.clone()
                g.apply_move(move[0], move[1], move[2])
                g._gen_turns_recursive(path + [move], results, limit)

        if not found_move:
            if path:
                results.append(tuple(path))

    # ------------------------------------------------------------------
    # Valid first moves (part of at least one maximal turn)
    # ------------------------------------------------------------------

    def valid_moves(self):
        """
        Return legal first moves that appear in at least one maximal turn.
        Each move is (from, to, die).
        """
        turns = self.generate_turns()
        # Handle the empty-turn case
        if turns == [()]:
            return []
        seen = set()
        moves = []
        for turn in turns:
            m = turn[0]
            key = (m[0], m[1], m[2])
            if key not in seen:
                seen.add(key)
                moves.append(m)
        return moves

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self):
        """Return a JSON-serialisable dictionary of the full game state."""
        legal = self.valid_moves() if self.dice and self.winner is None else []
        return {
            "board": self.board[:],
            "bar": self.bar[:],
            "off": self.off[:],
            "current_player": self.current_player,
            "dice": self.dice[:],
            "dice_rolled": self.dice_rolled[:],
            "winner": self.winner,
            "legal_moves": [list(m) for m in legal],
        }
