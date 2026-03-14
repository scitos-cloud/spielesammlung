# Adjacency list for 24 positions on the Nine Men's Morris board
#  0-----------1-----------2
#  |           |           |
#  |   3-------4-------5   |
#  |   |       |       |   |
#  |   |   6---7---8   |   |
#  |   |   |       |   |   |
#  9--10--11      12--13--14
#  |   |   |       |   |   |
#  |   |  15--16--17   |   |
#  |   |       |       |   |
#  |  18------19------20   |
#  |           |           |
# 21----------22----------23

ADJACENCY = {
    0: (1, 9),
    1: (0, 2, 4),
    2: (1, 14),
    3: (4, 10),
    4: (1, 3, 5, 7),
    5: (4, 13),
    6: (7, 11),
    7: (4, 6, 8),
    8: (7, 12),
    9: (0, 10, 21),
    10: (3, 9, 11, 18),
    11: (6, 10, 15),
    12: (8, 13, 17),
    13: (5, 12, 14, 20),
    14: (2, 13, 23),
    15: (11, 16),
    16: (15, 17, 19),
    17: (12, 16),
    18: (10, 19),
    19: (16, 18, 20, 22),
    20: (13, 19),
    21: (9, 22),
    22: (19, 21, 23),
    23: (14, 22),
}

# All 16 possible mills (triplets of positions)
MILLS = [
    # Outer square
    (0, 1, 2), (2, 14, 23), (21, 22, 23), (0, 9, 21),
    # Middle square
    (3, 4, 5), (5, 13, 20), (18, 19, 20), (3, 10, 18),
    # Inner square
    (6, 7, 8), (8, 12, 17), (15, 16, 17), (6, 11, 15),
    # Cross lines
    (1, 4, 7), (9, 10, 11), (12, 13, 14), (16, 19, 22),
]

# Pre-compute mills per position for fast lookup
MILLS_FOR_POS = {}
for i in range(24):
    MILLS_FOR_POS[i] = [m for m in MILLS if i in m]


class Board:
    """Immutable board representation for Nine Men's Morris."""

    __slots__ = ('_cells',)

    def __init__(self, cells=None):
        if cells is None:
            self._cells = (0,) * 24
        elif isinstance(cells, tuple):
            self._cells = cells
        else:
            self._cells = tuple(cells)

    @property
    def cells(self):
        return self._cells

    def __getitem__(self, pos):
        return self._cells[pos]

    def __hash__(self):
        return hash(self._cells)

    def __eq__(self, other):
        return isinstance(other, Board) and self._cells == other._cells

    def place(self, pos, player):
        """Return new board with player's stone placed at pos."""
        assert self._cells[pos] == 0, f"Position {pos} is not empty"
        lst = list(self._cells)
        lst[pos] = player
        return Board(tuple(lst))

    def move(self, from_pos, to_pos, player):
        """Return new board with player's stone moved from from_pos to to_pos."""
        assert self._cells[from_pos] == player, f"No stone of player {player} at {from_pos}"
        assert self._cells[to_pos] == 0, f"Position {to_pos} is not empty"
        lst = list(self._cells)
        lst[from_pos] = 0
        lst[to_pos] = player
        return Board(tuple(lst))

    def remove(self, pos):
        """Return new board with stone removed at pos."""
        assert self._cells[pos] != 0, f"No stone at position {pos}"
        lst = list(self._cells)
        lst[pos] = 0
        return Board(tuple(lst))

    def forms_mill(self, pos, player):
        """Check if player has a mill through position pos."""
        for mill in MILLS_FOR_POS[pos]:
            if all(self._cells[p] == player for p in mill):
                return True
        return False

    def is_in_mill(self, pos):
        """Check if the stone at pos is part of any mill."""
        player = self._cells[pos]
        if player == 0:
            return False
        return self.forms_mill(pos, player)

    def count_stones(self, player):
        return self._cells.count(player)

    def get_positions(self, player):
        return [i for i, c in enumerate(self._cells) if c == player]

    def to_list(self):
        return list(self._cells)
