from app.extensions import db
from datetime import datetime

class CV(db.Model):
    __tablename__ = "cvs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    cv_title = db.Column(db.String(255))
    original_filename = db.Column(db.String(255))
    storage_path = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="cvs")
    analyses = db.relationship("Analysis", back_populates="cv", cascade="all, delete-orphan")
    generated_cvs = db.relationship("GeneratedCV", back_populates="original_cv", cascade="all, delete-orphan")
