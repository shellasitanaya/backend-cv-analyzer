from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from pymysql import connect
from .extensions import *
from .models import *
from .routes.hr_routes import hr_bp
from .routes.js_routes import js_bp 
from app.routes.auth_routes import auth_bp
from app.database.seed.seed_all import seed_all  

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config) 
    CORS(app) # Mengaktifkan CORS untuk semua rute
    # CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})
    
    create_database_if_not_exists()

    # extensions initialization
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)

    app.register_blueprint(hr_bp)
    app.register_blueprint(js_bp) 

    app.register_blueprint(auth_bp, url_prefix="/api/auth")

    app.cli.add_command(seed_all)

    return app

def create_database_if_not_exists():
    host_parts = Config.DB_HOST.split(":")
    host = host_parts[0]
    port = int(host_parts[1]) if len(host_parts) > 1 else 3306  # default to 3306

    print(f"🔧 Ensuring database '{Config.DB_NAME}' exists...")
    print(f"Connecting to DB server at {host}:{port} with user '{Config.DB_USER}'")
    
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
