from flask import Blueprint, request, jsonify
from app.services.auth import AuthService

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["POST", "OPTIONS"])
def login():
    # Handle OPTIONS request for CORS preflight
    if request.method == "OPTIONS":
        print("✅ Handling OPTIONS preflight request")
        response = jsonify({"status": "success"})
        return response, 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "No JSON data provided"}), 400
            
        email = data.get("email")
        password = data.get("password")
        selected_role = data.get("role")

        print(f"🔐 Login attempt: {email}, role: {selected_role}")

        if not email or not password or not selected_role:
            return jsonify({"message": "Email, password and role are required"}), 400

        token, error = AuthService.authenticate_user(email, password, selected_role)
        if not token:
            return jsonify({
                "message": error
            }), 401

        return jsonify({"access_token": token}), 200
        
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        return jsonify({"message": "Internal server error"}), 500