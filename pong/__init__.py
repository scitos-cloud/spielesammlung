from flask import Blueprint

pong_bp = Blueprint('pong', __name__)

from pong import routes  # noqa: E402, F401
