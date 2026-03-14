from flask import Blueprint

dame_bp = Blueprint('dame', __name__, template_folder='../templates/dame')

from dame import routes  # noqa: E402, F401
