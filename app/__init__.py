from flask import Flask
from .routes import main_bp, admin_bd_bp
from db import create_db
from .routes_fasefinal import admin_fasefinal_bp
from .routes_jugador import jugador_bp
from dotenv import load_dotenv
import os

def create_app():
    load_dotenv()  # Carrega .env

    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")   # Secret per sessions
    create_db()

    app.config["ADMIN_PASSWORD"] = os.getenv("ADMIN_PASSWORD", "1234")

    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bd_bp)
    app.register_blueprint(admin_fasefinal_bp)
    app.register_blueprint(jugador_bp)
    
    return app



