from flask import Blueprint

maumau_bp = Blueprint('maumau', __name__)

from maumau import routes  # noqa: E402, F401
