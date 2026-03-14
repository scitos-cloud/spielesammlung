from flask import Blueprint

dame_bp = Blueprint('dame', __name__)

from dame import routes  # noqa: E402, F401
