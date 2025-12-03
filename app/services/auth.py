# app/services/auth.py
from flask_jwt_extended import create_access_token, decode_token
from datetime import timedelta
from app.models.user import User
from app.extensions import db, bcrypt

class AuthService:
    @staticmethod
    def authenticate_user(email, password, selected_role):
        """
        Check email & password using bcrypt, verify selected_role matches actual role.
        Return JWT if valid.
        """
        print(f"🔐 Auth attempt: {email}, role: {selected_role}")
        
        user = User.query.filter_by(email=email).first()
        
        # Check credentials
        if not user:
            print("❌ User not found")
            return None, "Invalid email or password"

        if not bcrypt.check_password_hash(user.password, password):
            print("❌ Invalid password")
            return None, "Invalid email or password"

        if user.role != selected_role:
            print(f"❌ Role mismatch: expected {selected_role}, got {user.role}")
            return None, f"This account does not have the {selected_role} role"

        print(f"✅ Auth successful for {email}, role: {user.role}")

        # Create JWT token
        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={
                "role": user.role,
                "email": user.email
            },
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
        
    @staticmethod
    def register(name, email, password, selected_role):
        """
        Create new user with the defined role.
        Return JWT after successful registration.
        """
        print(f"📝 Register attempt: name: {name}, email: {email}, role: {selected_role}")

        # Check if email already used
        existing = User.query.filter_by(email=email).first()
        if existing:
            print("❌ Email already registered")
            return None, "Email already registered"

        # Hash password
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

        # Create user
        user = User(
            name=name,
            email=email,
            password=hashed_password,
            role=selected_role
        )

        try:
            db.session.add(user)
            db.session.commit()
            print(f"✅ Registration successful for {email}")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Registration failed: {e}")
            return None, "Registration failed"

        # Create token after successful registration
        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={
                "role": user.role,
                "email": user.email
            },
            expires_delta=timedelta(hours=3)
        )

        return access_token, None