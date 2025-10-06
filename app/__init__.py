from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from pymysql import connect
from .extensions import db, migrate
from .models import *

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config) 
    CORS(app) # Mengaktifkan CORS untuk semua rute
    # CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})
    
    create_database_if_not_exists()
    db.init_app(app)
    migrate.init_app(app, db)

    from .routes.hr_routes import hr_bp
    app.register_blueprint(hr_bp)

    return app

def create_database_if_not_exists():
    host_parts = Config.DB_HOST.split(":")
    host = host_parts[0]
    port = int(host_parts[1]) if len(host_parts) > 1 else 3306  # default to 3306

    conn = connect(
        host=host,
        port=port,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {Config.DB_NAME}")
        conn.commit()
    finally:
        conn.close()
