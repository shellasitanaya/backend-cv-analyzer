from flask_jwt_extended import create_access_token, decode_token
from flask_bcrypt import check_password_hash
from datetime import timedelta
from app.models.user import User
from app.extensions import db

class AuthService:
    @staticmethod
    def authenticate_user(email, password):
        """Check email & password, return JWT if valid."""
        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            return None  # Invalid credentials

        # Create JWT token
        access_token = create_access_token(
            identity={"id": user.id, "role": user.role, "email": user.email},
            expires_delta=timedelta(hours=3)
        )
        return access_token

    @staticmethod
    def verify_token(token):
        """Decode token (for debugging or manual verification)."""
        try:
            decoded = decode_token(token)
            return decoded
        except Exception:
            return None
