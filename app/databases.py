from app.extensions import db
from app.models import Job, Candidate, GeneratedCV, Skill, CandidateSkill
import json

def get_all_jobs():
    """Ambil semua data pekerjaan, diubah ke dict."""
    jobs = Job.query.order_by(Job.created_at.desc()).all()
    return [job_to_dict(j) for j in jobs]



def get_job_by_id(job_id):
    """
    Ambil satu job berdasarkan ID.
    [FIX] Mengembalikan OBJEK SQLAlchemy, bukan dict.
    Route 'upload_and_process_cvs' Anda membutuhkan objek untuk mengakses job.min_gpa.
    """
    job = Job.query.get(job_id)
    return job # Mengembalikan objek, bukan job_to_dict(job)


def get_all_candidates_for_job(job_id, filters={}):
    """
    Ambil semua kandidat untuk satu job yang statusnya 'passed_filter'.
    [FIX] Menghapus filter GPA lama, karena filter itu terjadi di route
    dan kolom 'structured_profile_json' sudah tidak ada.
    """
    query = Candidate.query.filter_by(job_id=job_id, status='passed_filter')
    
    candidates = query.order_by(Candidate.match_score.desc()).all()
    return [candidate_to_dict(c) for c in candidates]




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


# Di databases.py

def candidate_to_dict(c: Candidate):
    
    # PERBAIKAN 1: Baca dari relasi 'candidate_skills'
    # c.candidate_skills adalah list [CandidateSkill, CandidateSkill]
    # cs.skill adalah objek Skill
    # cs.skill.skill_name adalah string nama skill-nya
    skills_list = [cs.skill.skill_name for cs in c.candidate_skills] if c.candidate_skills else []
    
    # PERBAIKAN 2: Konversi string JSON 'experience' kembali ke list
    experience_list = []
    if c.experience:
        try:
            experience_list = json.loads(c.experience)
        except json.JSONDecodeError:
            experience_list = [c.experience] # Fallback jika datanya teks biasa

    return {
        "id": c.id,
        "job_id": c.job_id,
        "original_filename": c.original_filename,
        "storage_path": c.storage_path,
        "name": c.name,
        "email": c.email,
        "phone": c.phone,
        "match_score": float(c.match_score) if c.match_score is not None else 0.0,
        "status": c.status,
        "rejection_reason": c.rejection_reason,
        "gpa": float(c.gpa) if c.gpa is not None else None,
        "education": c.education,
        "skills": skills_list, # Hasil dari Perbaikan 1
        "experience": experience_list, # Hasil dari Perbaikan 2
        "total_experience": c.total_experience 
    }
    
#  SKILLS
def get_or_create_skill(skill_name):
    """Fungsi helper untuk mencari skill atau membuatnya jika belum ada."""
    if not skill_name:
        return None
        
    skill_name_clean = skill_name.strip().title()
    
    # PERBAIKAN: Gunakan 'skill_name', bukan 'name'
    skill = Skill.query.filter_by(skill_name=skill_name_clean).first()
    
    if skill:
        return skill
    else:
        try:
            # PERBAIKAN: Gunakan 'skill_name', bukan 'name'
            skill = Skill(skill_name=skill_name_clean)
            db.session.add(skill)
            db.session.commit()
            return skill
        except Exception as e:
            db.session.rollback()
            print(f"Error get_or_create_skill: {e}")
            return Skill.query.filter_by(skill_name=skill_name_clean).first()

# SAVE CANDIDATE
def save_candidate(job_id, data):
    """
    Simpan data kandidat baru, TERMASUK memproses relasi skills 
    (menggunakan model CandidateSkill).
    """
    
    skill_strings = data.pop('skills', []) 
    
    # PERBAIKAN: Konversi list 'experience' menjadi string JSON
    experience_list = data.get('experience', [])
    experience_json_string = json.dumps(experience_list)

    new_candidate = Candidate(
        job_id=job_id,
        original_filename=data.get('original_filename'),
        storage_path=data.get('storage_path'),
        name=data.get('name'),
        email=data.get('email'),
        phone=data.get('phone'),
        match_score=data.get('score'), 
        status=data.get('status', 'processing'),
        rejection_reason=data.get('rejection_reason'),
        
        education=data.get('education'),
        gpa=data.get('gpa'),
        total_experience=data.get('total_experience'),
        
        # PERBAIKAN: Simpan string JSON ke kolom db.Text
        experience=experience_json_string 
    )
    
    try:
        # Simpan kandidat dulu agar dapat ID
        db.session.add(new_candidate)
        db.session.commit()

        # 3. Proses skills (setelah kandidat punya ID)
        if skill_strings:
            for skill_name in skill_strings:
                skill_obj = get_or_create_skill(skill_name) 
                if skill_obj:
                    # PERBAIKAN: Buat objek relasi CandidateSkill
                    new_link = CandidateSkill(
                        candidate_id=new_candidate.id, 
                        skill_id=skill_obj.id
                    )
                    db.session.add(new_link)
            
            # Commit lagi untuk menyimpan link skills
            db.session.commit()

        return new_candidate.id
    
    except Exception as e:
        db.session.rollback()
        print(f"Database error in save_candidate: {e}")
        return None
    
# simpan kandidat dari bulk upload
# def save_candidate(job_id, data):
#     """Simpan data kandidat ke database."""
#     candidate = Candidate(
#         job_id=job_id,
#         original_filename=data.get('original_filename'),
#         storage_path=data.get('storage_path'),
#         name=data.get('name'),
#         email=data.get('email'),
#         phone=data.get('phone'),
#         match_score=data.get('score'), 
#         status=data.get('status', 'processing'),
#         rejection_reason=data.get('rejection_reason'),
#         education=data.get('education'),
#         experience=data.get('experience')
#     )
#     db.session.add(candidate)
#     try:
#         db.session.commit()
#         return candidate.id
#     except Exception as e:
#         db.session.rollback()
#         print(f"Database error in save_candidate: {e}")
#         return None