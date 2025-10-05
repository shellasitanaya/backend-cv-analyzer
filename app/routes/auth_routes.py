from flask import Blueprint, request, jsonify
from app.services.auth import AuthService

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    selected_role = data.get("role")

    token, error = AuthService.authenticate_user(email, password, selected_role)
    if not token:
        return jsonify({
            "message": error
        }), 401

    return jsonify({"access_token": token}), 200
