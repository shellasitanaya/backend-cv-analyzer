from app.extensions import db
from app.models import Job, Candidate, GeneratedCV

def get_all_jobs():
    """Ambil semua data pekerjaan."""
    jobs = Job.query.order_by(Job.created_at.desc()).all()
    return [job_to_dict(j) for j in jobs]


def get_job_by_id(job_id):
    """Ambil satu job berdasarkan ID."""
    job = Job.query.get(job_id)
    return job_to_dict(job) if job else None


def get_all_candidates_for_job(job_id, filters={}):
    """Ambil semua kandidat untuk satu job dengan filter opsional."""
    query = Candidate.query.filter_by(job_id=job_id, status='passed_filter')

    # Contoh: jika ingin filter min_gpa dari structured_profile_json
    if 'min_gpa' in filters:
        # Gunakan filter JSON dengan SQLAlchemy text (jika perlu)
        from sqlalchemy import text
        query = query.filter(
            text(f"JSON_EXTRACT(structured_profile_json, '$.gpa') >= {filters['min_gpa']}")
        )

    candidates = query.order_by(Candidate.match_score.desc()).all()
    return [candidate_to_dict(c) for c in candidates]


def save_candidate(job_id, data):
    """Simpan data kandidat ke database."""
    candidate = Candidate(
        job_id=job_id,
        original_filename=data.get('original_filename'),
        storage_path=data.get('storage_path'),
        extracted_name=data.get('name'),
        extracted_email=data.get('email'),
        extracted_phone=data.get('phone'),
        match_score=data.get('score'),
        status=data.get('status', 'processing'),
        rejection_reason=data.get('rejection_reason'),
        structured_profile_json=data.get('structured_profile') or {}
    )
    db.session.add(candidate)
    try:
        db.session.commit()
        return candidate.id
    except Exception as e:
        db.session.rollback()
        print(f"Database error in save_candidate: {e}")
        return None

def save_generated_cv(original_cv_id: int, data: dict) -> int:
    """Menyimpan data CV yang di-generate ke tabel GeneratedCVs (ORM)."""
    try:
        new_cv = GeneratedCV(
            original_cv_id=original_cv_id,
            template_name=data.get('template_name'),
            version_number=data.get('version_number'),
            storage_path=data.get('storage_path')
        )
        db.session.add(new_cv)
        db.session.commit()
        return new_cv.id
    except Exception as e:
        db.session.rollback()
        print(f"Database error in save_generated_cv: {e}")
        return None


def get_last_cv_version(original_cv_id: int) -> int:
    """Mendapatkan nomor versi terakhir dari sebuah CV original (ORM)."""
    from sqlalchemy import func
    max_version = (
        db.session.query(func.max(GeneratedCV.version_number))
        .filter(GeneratedCV.original_cv_id == original_cv_id)
        .scalar()
    )
    return int(max_version) if max_version is not None else 0

# helper function
def job_to_dict(job: Job):
    return {
        "id": job.id,
        "job_title": job.job_title,
        "min_gpa": job.min_gpa,
        "degree_requirements": job.degree_requirements,
        "created_at": job.created_at.isoformat() if job.created_at else None
    }


def candidate_to_dict(c: Candidate):
    return {
        "id": c.id,
        "job_id": c.job_id,
        "original_filename": c.original_filename,
        "storage_path": c.storage_path,
        "extracted_name": c.extracted_name,
        "extracted_email": c.extracted_email,
        "extracted_phone": c.extracted_phone,
        "match_score": c.match_score,
        "status": c.status,
        "rejection_reason": c.rejection_reason,
        "structured_profile_json": c.structured_profile_json
    }