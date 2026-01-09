import os
from flask import Flask, current_app

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "CVPA1996")

DATABASE_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = DATABASE_URL is not None

# 🏐 Multi-torneig
TOURNAMENT_SLUG = os.environ.get("TOURNAMENT_SLUG", "default")
TOURNAMENT_TITLE = os.environ.get("TOURNAMENT_TITLE", "Torneig CVPA")


def create_app():
    app = Flask(__name__)

    # CONFIG
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["ADMIN_PASSWORD"] = ADMIN_PASSWORD
    app.config["DATABASE_URL"] = DATABASE_URL
    app.config["USE_POSTGRES"] = USE_POSTGRES

    # MULTI-TORNEIG CONFIG
    app.config["TOURNAMENT_SLUG"] = TOURNAMENT_SLUG
    app.config["TOURNAMENT_TITLE"] = TOURNAMENT_TITLE

    # Deixa variables disponibles a tots els templates
    @app.context_processor
    def inject_tournament():
        return {
            "TOURNAMENT_TITLE": current_app.config.get("TOURNAMENT_TITLE", "Torneig CVPA"),
            "TOURNAMENT_SLUG": current_app.config.get("TOURNAMENT_SLUG", "default"),
        }

    # INIT DB + MIGRATIONS (quan l'app ja existeix)
    with app.app_context():
        from db import ensure_db_exists
        ensure_db_exists()

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
