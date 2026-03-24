"""AdaptiveQuiz — Main Flask Application."""
import os
import json
import tempfile

from flask import Flask
from flask_login import LoginManager
from dotenv import load_dotenv

from backend.models import db, User

load_dotenv()


def create_app():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, "frontend", "templates"),
        static_folder=os.path.join(base_dir, "frontend", "static"),
        static_url_path="/static",
    )

    # ── Configuration ────────────────────────────────────────────
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "adaptive-quiz-dev-key-2026")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Database — use DATABASE_URL for PostgreSQL (Vercel), SQLite locally
    database_url = os.getenv("DATABASE_URL", "")
    if database_url:
        # Fix Heroku/Neon-style postgres:// → postgresql://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url

        # ── Connection-pool hardening (fixes dropped SSL connections) ──
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_pre_ping": True,        # test connection before every checkout
            "pool_recycle": 280,           # recycle connections every ~5 min
            "pool_size": 5,
            "max_overflow": 10,
            "connect_args": {
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 5,
            },
        }
    else:
        if os.environ.get("VERCEL"):
            db_path = os.path.join(tempfile.gettempdir(), "adaptive_quiz.db")
        else:
            db_path = os.path.join(os.path.dirname(__file__), "adaptive_quiz.db")
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    # Uploads
    app.config["UPLOAD_FOLDER"] = "/tmp/uploads"
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024  # 4MB (Vercel limit)

    # ── Extensions ───────────────────────────────────────────────
    db.init_app(app)

    login_manager = LoginManager(app)
    login_manager.login_view = "routes.login"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # JSON filter for templates
    @app.template_filter("from_json")
    def from_json_filter(value):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return {}

    # ── Blueprints ───────────────────────────────────────────────
    from backend.routes import routes_bp
    app.register_blueprint(routes_bp)

    # ── Create tables ────────────────────────────────────────────
    with app.app_context():
        db.create_all()

    return app


# Create the app instance (Vercel uses this)
app = create_app()


# For running directly
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
