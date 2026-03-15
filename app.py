import configparser
import os
from datetime import datetime, timezone
from flask import Flask
from extensions import db, login_manager, socketio, csrf
from models import User


def create_app(test_config=None):
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///spielesammlung.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # TwentyOne game config
    config = load_config()
    app.config['GAME_CONFIG'] = {
        'tie_rule': config.get('twentyone', 'tie_rule', fallback='dealer'),
        'num_decks': config.getint('twentyone', 'num_decks', fallback=1),
        'dealer_stand': config.getint('twentyone', 'dealer_stand', fallback=17),
    }

    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    socketio.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.before_request
    def update_last_seen():
        from flask_login import current_user
        if current_user.is_authenticated:
            current_user.last_seen = datetime.now(timezone.utc)
            db.session.commit()

    from auth import auth_bp
    from dashboard import dashboard_bp
    from dame import dame_bp
    from hangman import hangman_bp
    from muehle import muehle_bp
    from twentyone import twentyone_bp
    from backgammon import backgammon_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(dame_bp, url_prefix='/dame')
    app.register_blueprint(hangman_bp, url_prefix='/hangman')
    app.register_blueprint(muehle_bp, url_prefix='/muehle')
    app.register_blueprint(twentyone_bp, url_prefix='/twentyone')
    app.register_blueprint(backgammon_bp, url_prefix='/backgammon')

    # Import muehle socketio events
    with app.app_context():
        from muehle import events  # noqa: F401
        db.create_all()

    return app


def load_config():
    config = configparser.ConfigParser()
    config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
    return config


if __name__ == '__main__':
    config = load_config()
    app = create_app()
    socketio.run(
        app,
        host=config.get('server', 'host', fallback='0.0.0.0'),
        port=config.getint('server', 'port', fallback=5000),
        debug=config.getboolean('server', 'debug', fallback=False),
    )
