import json
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class DameGame(db.Model):
    __tablename__ = 'dame_game'
    id = db.Column(db.Integer, primary_key=True)
    white_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    black_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    is_ai_game = db.Column(db.Boolean, default=False)
    winner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    result = db.Column(db.String(20), nullable=True)
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at = db.Column(db.DateTime, nullable=True)

    white = db.relationship('User', foreign_keys=[white_id], backref='dame_games_as_white')
    black = db.relationship('User', foreign_keys=[black_id], backref='dame_games_as_black')
    winner = db.relationship('User', foreign_keys=[winner_id])


class MuehleGame(db.Model):
    __tablename__ = 'muehle_game'
    id = db.Column(db.Integer, primary_key=True)
    white_player_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    black_player_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    is_vs_computer = db.Column(db.Boolean, default=False)
    board_state = db.Column(db.Text, default=lambda: json.dumps([0] * 24))
    current_player = db.Column(db.Integer, default=1)
    stones_placed_white = db.Column(db.Integer, default=0)
    stones_placed_black = db.Column(db.Integer, default=0)
    pending_removal = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(16), default='waiting')
    winner = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at = db.Column(db.DateTime, nullable=True)

    white_player = db.relationship('User', foreign_keys=[white_player_id], backref='muehle_games_as_white')
    black_player = db.relationship('User', foreign_keys=[black_player_id], backref='muehle_games_as_black')
    moves = db.relationship('MuehleGameMove', backref='game', order_by='MuehleGameMove.move_number')

    def get_board(self):
        return json.loads(self.board_state)

    def set_board(self, board_list):
        self.board_state = json.dumps(board_list)

    def to_dict(self):
        return {
            'id': self.id,
            'board': self.get_board(),
            'current_player': self.current_player,
            'stones_placed_white': self.stones_placed_white,
            'stones_placed_black': self.stones_placed_black,
            'pending_removal': self.pending_removal,
            'status': self.status,
            'winner': self.winner,
            'is_vs_computer': self.is_vs_computer,
            'white_player': self.white_player.username,
            'black_player': self.black_player.username if self.black_player else None,
        }


class MuehleGameMove(db.Model):
    __tablename__ = 'muehle_game_move'
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('muehle_game.id'), nullable=False)
    move_number = db.Column(db.Integer, nullable=False)
    player = db.Column(db.Integer, nullable=False)
    action = db.Column(db.String(16), nullable=False)
    from_pos = db.Column(db.Integer, nullable=True)
    to_pos = db.Column(db.Integer, nullable=True)
    board_after = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
