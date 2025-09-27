from flask import Flask, jsonify
from flask_cors import CORS
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config) 
    CORS(app) # Mengaktifkan CORS untuk semua rute
    # CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})


    # @app.route('/api/test')
    # def test_route():
    #     return jsonify({"message": "Hello from Flask Backend!"})

    # Register blueprints (rute) Anda di sini nanti
    from .routes.hr_routes import hr_bp
    app.register_blueprint(hr_bp)

    return app