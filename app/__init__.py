import os
from flask import Flask

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "CVPA1996")

DATABASE_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = DATABASE_URL is not None


def create_app():
    app = Flask(__name__)

    # CONFIG
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["ADMIN_PASSWORD"] = ADMIN_PASSWORD
    app.config["DATABASE_URL"] = DATABASE_URL
    app.config["USE_POSTGRES"] = USE_POSTGRES

    # INIT DB + MIGRATIONS (quan l'app ja existeix)
    with app.app_context():
        from db import ensure_db_exists
        ensure_db_exists()

        # Migracions automàtiques DESPRÉS que existeixin les taules base
        from app.db_migrate import run_migration
        run_migration()

    # BLUEPRINTS
    from .routes import main_bp, admin_bd_bp
    from .routes_fasefinal import admin_fasefinal_bp
    from .routes_jugador import jugador_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bd_bp)
    app.register_blueprint(admin_fasefinal_bp)
    app.register_blueprint(jugador_bp)

    @app.route("/ping")
    def ping():
        return "pong"

    return app
