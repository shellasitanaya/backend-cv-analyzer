from app.extensions import db
from datetime import datetime

class GeneratedCV(db.Model):
    __tablename__ = "generatedcvs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    original_cv_id = db.Column(db.Integer, db.ForeignKey("cvs.id", ondelete="CASCADE"), nullable=False)
    template_name = db.Column(db.String(100))
    version_number = db.Column(db.Integer)
    storage_path = db.Column(db.String(255), nullable=False)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)

    original_cv = db.relationship("CV", back_populates="generated_cvs")
