from app.models import Candidate
from sqlalchemy import or_, func
from app.extensions import db

def search_candidates(keyword: str):
    """Cari kandidat berdasarkan nama, email, telepon, atau skill."""

    # gunakan lower-case untuk pencarian case-insensitive
    like_pattern = f"%{keyword}%"

    # cari di kolom nama, email, phone
    query = Candidate.query.filter(
        or_(
            func.lower(Candidate.extracted_name).like(like_pattern),
            func.lower(Candidate.extracted_email).like(like_pattern),
            func.lower(Candidate.extracted_phone).like(like_pattern),
            # JSON: cari keyword di dalam structured_profile_json -> 'hard_skills'
            func.lower(func.json_extract(Candidate.structured_profile_json, '$.hard_skills')).like(like_pattern)
        )
    ).all()

    # ubah ke bentuk JSON-friendly
    results = []
    for c in query:
        results.append({
            "id": c.id,
            "name": c.extracted_name,
            "email": c.extracted_email,
            "phone": c.extracted_phone,
            "match_score": float(c.match_score) if c.match_score else None,
            "status": c.status,
            "hard_skills": c.structured_profile_json.get("hard_skills", []) if c.structured_profile_json else [],
        })

    return results
