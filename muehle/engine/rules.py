from muehle.engine.board import Board, ADJACENCY


class GameState:
    """Full game state for Nine Men's Morris."""

    def __init__(self, board=None, current_player=1,
                 stones_placed=(0, 0), pending_removal=False):
        self.board = board or Board()
        self.current_player = current_player
        # stones_placed[0] = white placed, stones_placed[1] = black placed
        self.stones_placed = tuple(stones_placed)
        self.pending_removal = pending_removal

    def phase(self, player):
        """Return phase for player: 1=placing, 2=moving, 3=flying."""
        idx = player - 1
        if self.stones_placed[idx] < 9:
            return 1
        if self.board.count_stones(player) == 3:
            return 3
        return 2

    def opponent(self):
        return 3 - self.current_player

    def legal_actions(self):
        """Return list of legal actions as dicts."""
        if self.pending_removal:
            return self._removal_actions()

        player = self.current_player
        p = self.phase(player)

        if p == 1:
            return self._place_actions(player)
        elif p == 2:
            return self._move_actions(player)
        else:
            return self._fly_actions(player)

    def _place_actions(self, player):
        actions = []
        for pos in range(24):
            if self.board[pos] == 0:
                actions.append({'action': 'place', 'to_pos': pos})
        return actions

    def _move_actions(self, player):
        actions = []
        for from_pos in self.board.get_positions(player):
            for to_pos in ADJACENCY[from_pos]:
                if self.board[to_pos] == 0:
                    actions.append({'action': 'move', 'from_pos': from_pos, 'to_pos': to_pos})
        return actions

    def _fly_actions(self, player):
        actions = []
        for from_pos in self.board.get_positions(player):
            for to_pos in range(24):
                if self.board[to_pos] == 0:
                    actions.append({'action': 'fly', 'from_pos': from_pos, 'to_pos': to_pos})
        return actions

    def _removal_actions(self):
        opp = self.opponent()
        opp_positions = self.board.get_positions(opp)
        non_mill = [p for p in opp_positions if not self.board.is_in_mill(p)]
        # If all opponent stones are in mills, any can be removed
        targets = non_mill if non_mill else opp_positions
        return [{'action': 'remove', 'to_pos': p} for p in targets]

    def apply_action(self, action):
        """Apply action and return (new_state, formed_mill).

        formed_mill is True if the action formed a mill and the next
        state has pending_removal=True.
        """
        act = action['action']
        player = self.current_player

        if act == 'place':
            new_board = self.board.place(action['to_pos'], player)
            sp = list(self.stones_placed)
            sp[player - 1] += 1
            new_sp = tuple(sp)
            if new_board.forms_mill(action['to_pos'], player):
                return GameState(new_board, player, new_sp, pending_removal=True), True
            return GameState(new_board, self.opponent(), new_sp), False

        elif act in ('move', 'fly'):
            new_board = self.board.move(action['from_pos'], action['to_pos'], player)
            if new_board.forms_mill(action['to_pos'], player):
                return GameState(new_board, player, self.stones_placed, pending_removal=True), True
            return GameState(new_board, self.opponent(), self.stones_placed), False

        elif act == 'remove':
            new_board = self.board.remove(action['to_pos'])
            return GameState(new_board, self.opponent(), self.stones_placed), False

        raise ValueError(f"Unknown action: {act}")

    def check_winner(self):
        """Return winner (1 or 2) or None if game is ongoing.

        A player loses if they have fewer than 3 stones (after placing phase)
        or have no legal moves on their turn.
        """
        for player in (1, 2):
            if self.stones_placed[player - 1] >= 9:
                if self.board.count_stones(player) < 3:
                    return 3 - player  # opponent wins

        # If it's current player's turn and not removing, check mobility
        if not self.pending_removal:
            if not self.legal_actions():
                return self.opponent()

        return None

    def copy(self):
        return GameState(self.board, self.current_player,
                         self.stones_placed, self.pending_removal)
