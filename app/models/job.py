from app.extensions import db
from datetime import datetime
import uuid

class Job(db.Model):
    __tablename__ = "jobs"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    hr_user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_title = db.Column(db.String(255))
    job_location = db.Column(db.String(255))
    job_description = db.Column(db.Text)
    min_gpa = db.Column(db.Numeric(3, 2)) 
    min_experience = db.Column(db.Integer)
    max_experience = db.Column(db.Integer)
    degree_requirements = db.Column(db.String(100))
    requirements_json = db.Column(db.JSON)
    skills_json = db.Column(db.JSON)
    additional_info_json = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    hr_user = db.relationship("User", back_populates="jobs")
    candidates = db.relationship("Candidate", back_populates="job", cascade="all, delete-orphan")
