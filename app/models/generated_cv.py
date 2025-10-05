from app.extensions import db
from datetime import datetime
import uuid

class GeneratedCV(db.Model):
    __tablename__ = "generatedcvs"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    original_cv_id = db.Column(db.String(36), db.ForeignKey("cvs.id", ondelete="CASCADE"), nullable=False)
    template_name = db.Column(db.String(100))
    version_number = db.Column(db.Integer)
    storage_path = db.Column(db.String(255), nullable=False)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)

    original_cv = db.relationship("CV", back_populates="generated_cvs")
