import os

from dotenv import load_dotenv
from flask import Flask
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

# Initializes Flask extensions and registers app routes.
db = SQLAlchemy()
socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")


def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/smart_tasks"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    socketio.init_app(app)

    from app.api import api_bp
    from app.auth import auth_bp
    from app.views import views_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(views_bp)

    with app.app_context():
        db.create_all()

    return app
