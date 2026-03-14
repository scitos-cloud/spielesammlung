from flask import Blueprint

hangman_bp = Blueprint('hangman', __name__, template_folder='../templates/hangman')

from hangman import routes  # noqa: E402, F401
