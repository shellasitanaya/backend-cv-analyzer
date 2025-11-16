# app/models/candidate.py - tambahkan ini
from app.extensions import db
from datetime import datetime
import uuid

class Candidate(db.Model):
    __tablename__ = "candidates"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = db.Column(db.String(36), db.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    original_filename = db.Column(db.String(255))
    storage_path = db.Column(db.String(255))
    name = db.Column(db.String(255))
    email = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    match_score = db.Column(db.Numeric(5, 2))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    education = db.Column(db.Text, nullable=True)
    experience = db.Column(db.Text, nullable=True)

    status = db.Column(db.Enum("processing", "passed_filter", "rejected", name="candidate_status"), default="processing")
    rejection_reason = db.Column(db.String(255))

    job = db.relationship("Job", back_populates="candidates")
    candidate_skills = db.relationship("CandidateSkill", back_populates="candidate")

