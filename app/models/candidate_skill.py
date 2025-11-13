from app.extensions import db
import uuid

class CandidateSkill(db.Model):
    __tablename__ = "candidate_skills"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id = db.Column(db.String(36), db.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    skill_id = db.Column(db.String(36), db.ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)

    candidate = db.relationship("Candidate", back_populates="candidate_skills")
    skill = db.relationship("Skill", back_populates="candidate_skills")