import copy


class CheckersGame:
    """American Checkers (8x8) game logic.

    Board values: None=empty, 'w'=white, 'W'=white king, 'b'=black, 'B'=black king.
    White starts at bottom (rows 5-7), black at top (rows 0-2).
    White moves first.
    """

    def __init__(self):
        self.board = [[None] * 8 for _ in range(8)]
        self.turn = 'w'  # 'w' or 'b'
        self.winner = None  # 'w', 'b', or None
        self.captured = {'w': [], 'b': []}  # pieces captured BY each color
        self._setup_board()

    def _setup_board(self):
        for row in range(8):
            for col in range(8):
                if (row + col) % 2 == 1:
                    if row < 3:
                        self.board[row][col] = 'b'
                    elif row > 4:
                        self.board[row][col] = 'w'

    def clone(self):
        g = CheckersGame.__new__(CheckersGame)
        g.board = copy.deepcopy(self.board)
        g.turn = self.turn
        g.winner = self.winner
        g.captured = copy.deepcopy(self.captured)
        return g

    def to_dict(self):
        return {
            'board': self.board,
            'turn': self.turn,
            'winner': self.winner,
            'captured': self.captured,
        }

    def _owner(self, piece):
        if piece in ('w', 'W'):
            return 'w'
        if piece in ('b', 'B'):
            return 'b'
        return None

    def _is_king(self, piece):
        return piece in ('W', 'B')

    def _forward_dirs(self, color):
        """Return row directions for forward movement."""
        if color == 'w':
            return [-1]
        return [1]

    def _move_dirs(self, piece):
        """Return (row_dir, col_dir) pairs for a piece."""
        color = self._owner(piece)
        if self._is_king(piece):
            row_dirs = [-1, 1]
        else:
            row_dirs = self._forward_dirs(color)
        dirs = []
        for dr in row_dirs:
            for dc in [-1, 1]:
                dirs.append((dr, dc))
        return dirs

    def _in_bounds(self, r, c):
        return 0 <= r < 8 and 0 <= c < 8

    def get_jumps(self, row, col):
        """Get all possible jump sequences from (row, col). Returns list of move paths."""
        piece = self.board[row][col]
        if piece is None:
            return []
        results = []
        self._find_jumps(row, col, piece, [], set(), results)
        return results

    def _find_jumps(self, row, col, piece, path, captured, results):
        found_jump = False
        for dr, dc in self._move_dirs(piece):
            mr, mc = row + dr, col + dc
            lr, lc = row + 2 * dr, col + 2 * dc
            if not self._in_bounds(lr, lc):
                continue
            mid = self.board[mr][mc]
            if mid is None or self._owner(mid) == self._owner(piece):
                continue
            if (mr, mc) in captured:
                continue
            if self.board[lr][lc] is not None:
                continue
            found_jump = True
            new_captured = captured | {(mr, mc)}
            # Check if piece becomes king upon landing
            promoted = self._would_promote(piece, lr)
            new_piece = piece.upper() if promoted else piece
            new_path = path + [(lr, lc)]
            # Save board state, simulate jump
            old_mid = self.board[mr][mc]
            old_dest = self.board[lr][lc]
            old_src = self.board[row][col]
            self.board[mr][mc] = None
            self.board[lr][lc] = new_piece
            self.board[row][col] = None
            # If promoted, stop multi-jump (American checkers rule)
            if promoted:
                results.append(new_path)
            else:
                self._find_jumps(lr, lc, new_piece, new_path, new_captured, results)
            # Restore
            self.board[row][col] = old_src
            self.board[mr][mc] = old_mid
            self.board[lr][lc] = old_dest

        if not found_jump and path:
            results.append(path)

    def _would_promote(self, piece, dest_row):
        if self._is_king(piece):
            return False
        color = self._owner(piece)
        if color == 'w' and dest_row == 0:
            return True
        if color == 'b' and dest_row == 7:
            return True
        return False

    def get_simple_moves(self, row, col):
        """Get non-jump moves from (row, col)."""
        piece = self.board[row][col]
        if piece is None:
            return []
        moves = []
        for dr, dc in self._move_dirs(piece):
            nr, nc = row + dr, col + dc
            if self._in_bounds(nr, nc) and self.board[nr][nc] is None:
                moves.append([(nr, nc)])
        return moves

    def get_all_moves(self, color):
        """Get all legal moves for a color. Returns dict {(r,c): [move_paths]}."""
        jumps = {}
        simple = {}
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if piece is None or self._owner(piece) != color:
                    continue
                j = self.get_jumps(r, c)
                if j:
                    jumps[(r, c)] = j
                s = self.get_simple_moves(r, c)
                if s:
                    simple[(r, c)] = s
        # Mandatory capture: if any jumps exist, only jumps are legal
        if jumps:
            return jumps
        return simple

    def get_valid_moves_for_piece(self, row, col):
        """Get valid moves for a specific piece, considering mandatory capture."""
        piece = self.board[row][col]
        if piece is None or self._owner(piece) != self.turn:
            return []
        all_moves = self.get_all_moves(self.turn)
        return all_moves.get((row, col), [])

    def make_move(self, from_row, from_col, path):
        """Execute a move. path is list of (row, col) destinations.
        Returns True if valid, False otherwise."""
        if self.winner:
            return False
        piece = self.board[from_row][from_col]
        if piece is None or self._owner(piece) != self.turn:
            return False

        valid_moves = self.get_valid_moves_for_piece(from_row, from_col)
        # Normalize path for comparison
        path_tuples = [tuple(p) for p in path]
        if path_tuples not in [list(map(tuple, m)) for m in valid_moves]:
            return False

        # Execute the move
        cr, cc = from_row, from_col
        for dest_r, dest_c in path_tuples:
            dr = dest_r - cr
            dc = dest_c - cc
            if abs(dr) == 2:
                # Jump - remove captured piece
                mr, mc = cr + dr // 2, cc + dc // 2
                captured_piece = self.board[mr][mc]
                if captured_piece:
                    self.captured[self._owner(piece)].append(captured_piece)
                self.board[mr][mc] = None
            self.board[dest_r][dest_c] = piece
            self.board[cr][cc] = None
            cr, cc = dest_r, dest_c
            # Check promotion
            if self._would_promote(piece, cr):
                piece = piece.upper()
                self.board[cr][cc] = piece

        # Switch turn
        self.turn = 'b' if self.turn == 'w' else 'w'

        # Check for game over
        if not self.get_all_moves(self.turn):
            self.winner = 'w' if self.turn == 'b' else 'b'

        return True

    def count_pieces(self, color):
        count = 0
        for row in self.board:
            for piece in row:
                if piece and self._owner(piece) == color:
                    count += 1
        return count
