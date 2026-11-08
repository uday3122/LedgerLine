
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager

db = SQLAlchemy()
jwt = JWTManager()


def create_app():
    app = Flask(__name__)

    from config import Config
    Config.validate()

    app.config.from_object(Config)

    db.init_app(app)
    jwt.init_app(app)

    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    from app.routes.accounts import accounts_bp
    app.register_blueprint(accounts_bp)

    from app.routes.transactions import transactions_bp
    app.register_blueprint(transactions_bp)

    return app
