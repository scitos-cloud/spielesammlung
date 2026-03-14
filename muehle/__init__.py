from flask import Blueprint

muehle_bp = Blueprint('muehle', __name__, template_folder='../templates/muehle')

from muehle import routes  # noqa: E402, F401
