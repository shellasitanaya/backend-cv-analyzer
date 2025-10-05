from app.extensions import db
from datetime import datetime

class Candidate(db.Model):
    __tablename__ = "candidates"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    original_filename = db.Column(db.String(255))
    storage_path = db.Column(db.String(255))
    extracted_name = db.Column(db.String(255))
    extracted_email = db.Column(db.String(255))
    extracted_phone = db.Column(db.String(50))
    match_score = db.Column(db.Numeric(5, 2))
    structured_profile_json = db.Column(db.JSON)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    status = db.Column(db.Enum("processing", "passed_filter", "rejected", name="candidate_status"), default="processing")
    rejection_reason = db.Column(db.String(255))

    job = db.relationship("Job", back_populates="candidates")
