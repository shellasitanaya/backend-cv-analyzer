from flask_jwt_extended import create_access_token, decode_token
from werkzeug.security import check_password_hash
from datetime import timedelta
from app.models.user import User
from app.extensions import db

class AuthService:
    @staticmethod
    def authenticate_user(email, password, selected_role):
        """
        Check email & password, verify selected_role matches actual role.
        Return JWT if valid.
        """
        user = User.query.filter_by(email=email).first()
        
        # Check credentials
        if not user or not check_password_hash(user.password, password):
            return None, "Invalid email or password"

        if user.role != selected_role:
            return None, f"This account does not have the {selected_role} role"

        # Create JWT token
        access_token = create_access_token(
            identity={"id": user.id, "role": user.role, "email": user.email},
            expires_delta=timedelta(hours=3)
        )
        return access_token, None


    @staticmethod
    def verify_token(token):
        """Decode token (for debugging or manual verification)."""
        try:
            decoded = decode_token(token)
            return decoded
        except Exception:
            return None
