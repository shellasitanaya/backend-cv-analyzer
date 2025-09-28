# File: app/__init__.py

# ... (kode yang sudah ada)

def create_app():
    app = Flask(__name__)
    # ... (kode yang sudah ada)

    # Register blueprints
    from .routes.hr_routes import hr_bp
    from .routes.js_routes import js_bp 

    app.register_blueprint(hr_bp)
    app.register_blueprint(js_bp) 

    return app