from flask import Blueprint

hangman_bp = Blueprint('hangman', __name__)

from hangman import routes  # noqa: E402, F401
