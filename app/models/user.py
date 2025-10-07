from ..extensions import db 
from datetime import datetime
import uuid
from sqlalchemy.dialects.mysql import JSON  # tambahkan ini


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255))
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum("user", "hr", "admin", name="user_roles"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    cvs = db.relationship("CV", back_populates="user", cascade="all, delete-orphan")
    jobs = db.relationship("Job", back_populates="hr_user", cascade="all, delete-orphan")

    # for string representation
    def __repr__(self):
        return f"<User {self.email}>"