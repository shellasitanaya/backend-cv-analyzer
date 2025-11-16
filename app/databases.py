from app.extensions import db
from app.models import Job, Candidate, GeneratedCV, CV, Analysis, User
from datetime import datetime
import uuid
import os


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

# ==================== JOB SEEKER FUNCTIONS (NEW) ====================

def save_user_cv(user_id, cv_data, analysis_data):
    """
    Simpan CV user dan hasil analisis ke database
    """
    try:
        # Simpan CV
        new_cv = CV(
            id=str(uuid.uuid4()),
            user_id=user_id,
            cv_title=cv_data.get('cv_title', 'Untitled CV'),
            original_filename=cv_data.get('original_filename'),
            storage_path=cv_data.get('storage_path'),
            uploaded_at=datetime.utcnow()
        )
        db.session.add(new_cv)

        # Simpan Analysis
        new_analysis = Analysis(
            id=str(uuid.uuid4()),
            cv_id=new_cv.id,
            job_description_text=analysis_data.get('job_description_text', ''),
            match_score=analysis_data.get('match_score'),
            ats_check_result_json=analysis_data.get('ats_check_result_json'),
            keyword_analysis_json=analysis_data.get('keyword_analysis_json'),
            analyzed_at=datetime.utcnow()
        )
        db.session.add(new_analysis)

        db.session.commit()
        return {
            "cv_id": new_cv.id,
            "analysis_id": new_analysis.id
        }
    except Exception as e:
        db.session.rollback()
        print(f"Database error in save_user_cv: {e}")
        return None

def get_user_cvs_with_analyses(user_id):
    """
    Ambil semua CV user beserta analisis terbaru
    """
    try:
        cvs = CV.query.filter_by(user_id=user_id).order_by(CV.uploaded_at.desc()).all()
        
        result = []
        for cv in cvs:
            # Get latest analysis for this CV
            latest_analysis = Analysis.query.filter_by(cv_id=cv.id).order_by(Analysis.analyzed_at.desc()).first()
            
            cv_data = {
                "cv_id": cv.id,
                "cv_title": cv.cv_title,
                "original_filename": cv.original_filename,
                "uploaded_at": cv.uploaded_at.isoformat() if cv.uploaded_at else None,
                "latest_analysis": None
            }
            
            if latest_analysis:
                cv_data["latest_analysis"] = {
                    "analysis_id": latest_analysis.id,
                    "match_score": float(latest_analysis.match_score) if latest_analysis.match_score else 0,
                    "analyzed_at": latest_analysis.analyzed_at.isoformat() if latest_analysis.analyzed_at else None,
                    "job_description_preview": latest_analysis.job_description_text[:100] + "..." if latest_analysis.job_description_text else ""
                }
            
            result.append(cv_data)
        
        return result
    except Exception as e:
        print(f"Database error in get_user_cvs_with_analyses: {e}")
        return []

def get_analysis_detail(analysis_id, user_id):
    """
    Ambil detail analisis spesifik dengan validasi ownership
    """
    try:
        analysis = db.session.query(Analysis).\
            join(CV, Analysis.cv_id == CV.id).\
            filter(Analysis.id == analysis_id, CV.user_id == user_id).\
            first()
        
        if not analysis:
            return None
        
        return {
            "analysis_id": analysis.id,
            "cv_id": analysis.cv_id,
            "job_description": analysis.job_description_text,
            "match_score": float(analysis.match_score) if analysis.match_score else 0,
            "ats_check_result": analysis.ats_check_result_json or {},
            "keyword_analysis": analysis.keyword_analysis_json or {},
            "analyzed_at": analysis.analyzed_at.isoformat() if analysis.analyzed_at else None
        }
    except Exception as e:
        print(f"Database error in get_analysis_detail: {e}")
        return None

def delete_user_cv(cv_id, user_id):
    """
    Hapus CV user dan semua analisis terkait
    """
    try:
        cv = CV.query.filter_by(id=cv_id, user_id=user_id).first()
        
        if not cv:
            return False

        # Hapus file dari storage
        if os.path.exists(cv.storage_path):
            os.remove(cv.storage_path)

        # Hapus dari database (cascade akan menghapus analyses juga)
        db.session.delete(cv)
        db.session.commit()
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"Database error in delete_user_cv: {e}")
        return False

# ==================== HELPER FUNCTIONS ====================

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

def cv_to_dict(cv: CV):
    """Helper function untuk convert CV object ke dictionary"""
    return {
        "cv_id": cv.id,
        "user_id": cv.user_id,
        "cv_title": cv.cv_title,
        "original_filename": cv.original_filename,
        "storage_path": cv.storage_path,
        "uploaded_at": cv.uploaded_at.isoformat() if cv.uploaded_at else None
    }

def analysis_to_dict(analysis: Analysis):
    """Helper function untuk convert Analysis object ke dictionary"""
    return {
        "analysis_id": analysis.id,
        "cv_id": analysis.cv_id,
        "job_description": analysis.job_description_text,
        "match_score": float(analysis.match_score) if analysis.match_score else 0,
        "ats_check_result": analysis.ats_check_result_json or {},
        "keyword_analysis": analysis.keyword_analysis_json or {},
        "analyzed_at": analysis.analyzed_at.isoformat() if analysis.analyzed_at else None
    }