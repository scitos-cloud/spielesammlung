from flask import Blueprint

backgammon_bp = Blueprint('backgammon', __name__)

from backgammon import routes  # noqa: E402, F401
