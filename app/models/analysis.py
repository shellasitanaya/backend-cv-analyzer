from app.extensions import db
from datetime import datetime
import uuid

class Analysis(db.Model):
    __tablename__ = "analyses"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    cv_id = db.Column(db.String(36), db.ForeignKey("cvs.id", ondelete="CASCADE"), nullable=False)
    job_description_text = db.Column(db.Text, nullable=False)
    match_score = db.Column(db.Numeric(5, 2))
    ats_check_result_json = db.Column(db.JSON)
    keyword_analysis_json = db.Column(db.JSON)
    phrasing_suggestions_json = db.Column(db.JSON)
    analyzed_at = db.Column(db.DateTime, default=datetime.utcnow)

    cv = db.relationship("CV", back_populates="analyses")
