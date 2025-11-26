import os
from flask import Flask
from flask import g

# ----------------------------------------
# 🔧 DETECTAR SI SOM A PRODUCCIÓ (RENDER)
# ----------------------------------------
IS_RENDER = os.environ.get("RENDER") == "true"

# ----------------------------------------
# 🔐 CONFIGURACIÓ SECRETA
# ----------------------------------------
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "1234")

# ----------------------------------------
# 🗄 BASE DE DADES
# ----------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL")  # PostgreSQL Neon
USE_POSTGRES = DATABASE_URL is not None  # True si existeix


def create_app():
    """
    Crea l'aplicació Flask i carrega:
    - Config global
    - Rutes
    - DB inicial (Postgres o SQLite)
    """

    app = Flask(__name__)

    # -----------------------------
    # 🔐 CONFIG DE L’APP
    # -----------------------------
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["ADMIN_PASSWORD"] = ADMIN_PASSWORD
    app.config["DATABASE_URL"] = DATABASE_URL
    app.config["USE_POSTGRES"] = USE_POSTGRES

    # -----------------------------
    # 🗄 INICIALITZAR DB SI CAL
    # -----------------------------
    from db import ensure_db_exists
    ensure_db_exists()

    # -----------------------------
    # 📌 IMPORTAR I REGISTRAR BLUEPRINTS
    # -----------------------------
    from .routes_main import main_bp
    from .routes_admin import admin_bp
    from .routes_fasegrups import admin_bd_bp
    from .routes_fasefinal import admin_fasefinal_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(admin_bd_bp)
    app.register_blueprint(admin_fasefinal_bp)

    # -----------------------------
    # 🌍 TEST ROUTE (opcional)
    # -----------------------------
    @app.route("/ping")
    def ping():
        return "pong"

    return app

