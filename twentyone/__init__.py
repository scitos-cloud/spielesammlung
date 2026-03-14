from flask import Blueprint

twentyone_bp = Blueprint('twentyone', __name__, template_folder='../templates/twentyone')

from twentyone import routes  # noqa: E402, F401
