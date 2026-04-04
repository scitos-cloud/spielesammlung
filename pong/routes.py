from flask import render_template
from flask_login import login_required
from pong import pong_bp


@pong_bp.route('/')
@login_required
def index():
    return render_template('pong/index.html')
