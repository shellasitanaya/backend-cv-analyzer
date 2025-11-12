from app.extensions import db
import uuid

class Skill(db.Model):
    __tablename__ = "skills"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    skill_name = db.Column(db.String(255))

    candidate_skills = db.relationship("CandidateSkill", back_populates="skill")