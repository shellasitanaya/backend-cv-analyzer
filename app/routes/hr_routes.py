from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity,
)
import os
import json
import pprint
from app.extensions import db
from app.models import Job
from app.models import Candidate, CandidateSkill, Skill
from app.services.cv_parser import extract_text
from app.services.ai_analyzer import (
    parse_candidate_info,
    get_ai_match_score,
    # calculate_match_score,
    BUSINESS_ANALYST_SKILLS,
    DATA_ENGINEER_SKILLS,
)
from app.services.ai_analyzer import parse_candidate_info, calculate_match_score
import app.databases as databases
from app.services.talent_search import search_candidates
from werkzeug.utils import secure_filename
from flask import jsonify, request




hr_bp = Blueprint("hr_api", __name__, url_prefix="/api/hr")
candidate_bp = Blueprint('candidate', __name__, url_prefix='/api/candidates')

UPLOAD_FOLDER = "temp_uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# upload and process multiple CVs (bulk upload) -> terima dari front
@hr_bp.route("/jobs/<job_id>/upload", methods=["POST"])
def upload_and_process_cvs(job_id):
    if "cv_files" not in request.files or not request.files.getlist("cv_files"):
        print("!!! [ERROR] 'cv_files' not found in request.files !!!")
        return jsonify({"error": "No 'cv_files' found in request"}), 400

    cv_files = request.files.getlist("cv_files")

    job = databases.get_job_by_id(job_id)
    if not job:
        return jsonify({"error": "Job ID not found"}), 404

    job_requirements = {"min_gpa": job.min_gpa, "min_experience": job.min_experience, "degree_requirements": job.degree_requirements}
    job_description = job.job_description or ""

    job_title_lower = (
        job.job_title.lower()
    )  # Ambil judul pekerjaan, cth: "it data engineer - taf"
    selected_skills_list = []

    # Pilih list skill berdasarkan kata kunci di judul pekerjaan
    if "data engineer" in job_title_lower:
        selected_skills_list = DATA_ENGINEER_SKILLS
        print(
            f"[DEBUG] Memakai skill list: DATA_ENGINEER_SKILLS untuk job '{job.job_title}'"
        )

    elif "business analyst" in job_title_lower:
        selected_skills_list = BUSINESS_ANALYST_SKILLS
        print(
            f"[DEBUG] Memakai skill list: BUSINESS_ANALYST_SKILLS untuk job '{job.job_title}'"
        )

    else:
        # Fallback jika judul pekerjaan tidak cocok
        print(f"[WARNING] Tidak ada list skill hardcoded untuk job: {job.job_title}")
        selected_skills_list = []  # Kosongkan jika tidak ada yg cocok

    # Pastikan semua skill dalam huruf kecil untuk dicocokkan
    required_skills_lower = [skill.lower() for skill in selected_skills_list]

    report = {"passed_count": 0, "rejected_count": 0, "rejection_details": {}}

    for cv_file in cv_files:
        filename = secure_filename(cv_file.filename)
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)
        file_path = os.path.join(UPLOAD_FOLDER, filename)

        try:
            cv_file.save(file_path)
            cv_text = extract_text(file_path)

            structured_profile = parse_candidate_info(
                cv_text, required_skills=required_skills_lower
            )

            # DEBUG: print structured profile
            print(f"[DEBUG] Hasil Parsing (Structured Profile) dari: {filename}")
            pprint.pprint(structured_profile)
            print("=" * 60)

            rejection_reason = None

            # --- PERBAIKAN VALIDASI TIPE DATA (PENTING) ---
            gpa_raw = structured_profile.get("gpa")
            exp_raw = structured_profile.get("total_experience")
            edu_raw = structured_profile.get("education")

            candidate_gpa = None
            if isinstance(gpa_raw, (int, float)):
                candidate_gpa = gpa_raw

            candidate_experience = None
            if isinstance(exp_raw, int):
                candidate_experience = exp_raw
            
            EDUCATION_LEVELS = {"D3": 1, "S1": 2, "S2": 3, "S3": 4}
            
            # Tentukan level kandidat (dari parser)
            candidate_edu_level = 0
            if edu_raw:
                edu_upper = edu_raw.upper()
                if "S3" in edu_upper or "DOCTORATE" in edu_upper or "PHD" in edu_upper: 
                    candidate_edu_level = EDUCATION_LEVELS["S3"]
                elif "S2" in edu_upper or "MASTER" in edu_upper or "MAGISTER" in edu_upper: 
                    candidate_edu_level = EDUCATION_LEVELS["S2"]
                elif "S1" in edu_upper or "BACHELOR" in edu_upper or "SARJANA" in edu_upper: 
                    candidate_edu_level = EDUCATION_LEVELS["S1"]
                elif "D3" in edu_upper or "DIPLOMA" in edu_upper: 
                    candidate_edu_level = EDUCATION_LEVELS["D3"]
            
            # Tentukan level minimum dari lowongan (Job)
            required_edu_level = 0
            if job_requirements["degree_requirements"]:
                req_upper = job_requirements["degree_requirements"].upper()
                
                if "S3" in req_upper or "DOCTORATE" in req_upper or "PHD" in req_upper:
                    required_edu_level = EDUCATION_LEVELS["S3"]
                elif "S2" in req_upper or "MASTER" in req_upper or "MAGISTER" in req_upper:
                    required_edu_level = EDUCATION_LEVELS["S2"]
                elif "S1" in req_upper or "BACHELOR" in req_upper or "SARJANA" in req_upper:
                    required_edu_level = EDUCATION_LEVELS["S1"]
                elif "D3" in req_upper or "DIPLOMA" in req_upper:
                    required_edu_level = EDUCATION_LEVELS["D3"]
            # ----------------------------------------------------
            # -----------------------------------------------

            rejection_reasons = []  # <--- INI YANG HILANG SEBELUMNYA

            # 1. Cek GPA
            if job_requirements["min_gpa"] is not None:
                if candidate_gpa is None:
                    rejection_reasons.append("GPA not found/invalid") 
                elif candidate_gpa < job_requirements["min_gpa"]:
                    rejection_reasons.append( f"GPA below minimum requirement ({job_requirements['min_gpa']})")

            # 2. Cek Experience
            if job_requirements.get("min_experience") is not None:
                if candidate_experience is None:
                    rejection_reasons.append("Experience not found")
                elif candidate_experience < job_requirements.get("min_experience"):
                    rejection_reasons.append(f"Experience below minimum requirement ({job_requirements.get('min_experience')} years)")

            # 3. Cek Education
            if required_edu_level > 0:
                if candidate_edu_level < required_edu_level:
                    rejection_reasons.append(f"Education below minimum requirement ({job_requirements['degree_requirements']})")


            # --- PREPARE DATA UNTUK DISIMPAN ---``
            candidate_data = {
                "original_filename": filename,
                "storage_path": file_path,
                "name": structured_profile.get("name"),
                "email": structured_profile.get("email"),
                "phone": structured_profile.get("phone"),
                "gpa": structured_profile.get("gpa"),
                "education": structured_profile.get("education"),
                "experience": structured_profile.get("experience"),  
                "total_experience": structured_profile.get("total_experience"),  
                "skills": structured_profile.get("skills"),  
                "scoring_reason": None
            }

            # --- PENENTUAN STATUS AKHIR ---
            if len(rejection_reasons) > 0:
                # GABUNGKAN SEMUA ALASAN MENJADI SATU STRING
                final_reason = "; ".join(rejection_reasons)

                report["rejected_count"] += 1
                report["rejection_details"][final_reason] = (
                    report["rejection_details"].get(final_reason, 0) + 1
                )

                candidate_data["status"] = "rejected"
                candidate_data["rejection_reason"] = final_reason # Simpan string gabungan

                print(f"[DEBUG] Rejected: {filename} -> {final_reason}")
                databases.save_candidate(job_id, candidate_data)

            else:
                # LOLOS FILTER -> LANJUT KE AI SCORING
                report["passed_count"] += 1
                
                ai_result = get_ai_match_score(cv_text, job_description) 
                
                print(f"[DEBUG] AI Scoring Result for {filename}: {ai_result}")
                
                candidate_data['status'] = 'passed_filter'
                candidate_data['score'] = ai_result.get('match_score', 0)
                candidate_data["scoring_reason"] = ai_result.get("reasoning")

                databases.save_candidate(job_id, candidate_data)
                
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            import traceback

            traceback.print_exc()  # Tambahkan ini untuk debug lebih detail
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    return jsonify(report), 200

@hr_bp.route('/jobs/<job_id>/candidates', methods=['GET'])
def get_ranked_candidates(job_id):
    """
    Endpoint untuk mengambil kandidat yang sudah di-ranking untuk sebuah
    pekerjaan, dengan support untuk filter dinamis.
    """
    try:
        # Ambil parameter filter dari URL (e.g., ?min_gpa=3.0&skills=React,Python)
        filters = {
            'min_gpa': request.args.get('min_gpa'),
            'min_exp': request.args.get('min_exp'),
            'skills': request.args.get('skills')
        }
        
        # Hapus filter yang nilainya kosong
        active_filters = {k: v for k, v in filters.items() if v}
        
        if 'min_exp' in active_filters:
            active_filters['total_experience'] = active_filters.pop('min_exp')
        
        # Panggil fungsi database dengan filter yang sudah bersih
        candidates = databases.get_all_candidates_for_job(job_id, active_filters)
        
        return jsonify(candidates)
    
    except Exception as e:
        import traceback
        print(f"!!! ERROR in get_ranked_candidates: {e}") 
        traceback.print_exc()
        return jsonify({"error": f"Gagal mengambil data dari database: {e}"}), 500
    

@hr_bp.route('/candidates/search', methods=['GET'])
def search_candidates_endpoint():
    try:
        keyword = request.args.get("q", "")
        if not keyword:
            return jsonify({
                "status": "success",
                "message": "Keyword not found, no results",
                "data": []
            }), 200

        results = search_candidates(keyword)

        return jsonify({
            "status": "success",
            "message": f"{len(results)} candidate found with the keyword '{keyword}'",
            "data": results
        }), 200

    except Exception as e:
        print("ERROR search_candidates:", e)
        return jsonify({
            "status": "error",
            "message": "There has been a mistake finding a candidate",
            "data": [],
            "details": str(e)
        }), 500

# Endpoint untuk profil detail (lakukan hal yang sama)
@candidate_bp.route('/<candidate_id>', methods=['GET'])
def get_candidate(candidate_id):
    try:
        candidate = Candidate.query.get(candidate_id)
        if not candidate:
            return jsonify({'error': 'Candidate not found'}), 404
        
        return jsonify({
            'id': candidate.id,
            'name': candidate.name,
            'email': candidate.email,
            'phone': candidate.phone,
            'match_score': candidate.match_score,
            'education': candidate.education,
            'experience': candidate.experience,
            'status': candidate.status,
            'original_filename': candidate.original_filename,
            'storage_path': candidate.storage_path,
            'uploaded_at': candidate.uploaded_at.isoformat() if candidate.uploaded_at else None,
            'job_id': candidate.job_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@hr_bp.route("/jobs", methods=["GET"])
def get_jobs_list():
    """Endpoint untuk mengambil semua data pekerjaan."""
    try:
        jobs = databases.get_all_jobs()
        return jsonify(jobs)
    except Exception as e:
        return jsonify({"error": "Failed to fetch job list", "details": str(e)}), 500
    
@candidate_bp.route('/<candidate_id>/skills', methods=['GET'])
def get_candidate_skills(candidate_id):
    try:
        print(f"🔍 [DEBUG] Mencari skills untuk candidate: {candidate_id}")
        
        candidate = Candidate.query.get(candidate_id)
        if not candidate:
            return jsonify({'error': 'Candidate not found'}), 404
        
        # Gunakan skill.skill_name bukan skill.name
        candidate_skills = db.session.query(Skill).join(
            CandidateSkill, Skill.id == CandidateSkill.skill_id
        ).filter(
            CandidateSkill.candidate_id == candidate_id
        ).all()
        
        skills = []
        for skill in candidate_skills:
            skills.append({
                'id': skill.id,
                'name': skill.skill_name,  # PASTIKAN skill.skill_name
                'category': skill.category if hasattr(skill, 'category') else 'General'
            })
        
        print(f"✅ [DEBUG] Ditemukan {len(skills)} skills untuk {candidate.name}")
        
        return jsonify({
            'candidate_id': candidate_id,
            'candidate_name': candidate.name,
            'skills': skills
        })
        
    except Exception as e:
        print(f"💥 [ERROR] get_candidate_skills: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@candidate_bp.route('/', methods=['GET'])
def get_all_candidates():
    try:
        candidates = Candidate.query.all()
        return jsonify([{
            'id': candidate.id,
            'name': candidate.name,
            'email': candidate.email,
            'match_score': candidate.match_score,
            'status': candidate.status,
            'uploaded_at': candidate.uploaded_at.isoformat() if candidate.uploaded_at else None
        } for candidate in candidates])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# JOB POSTING ROUTES
@hr_bp.route("/jobs/create", methods=["POST"])
@jwt_required()
def create_job():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        job = Job(
            hr_user_id=user_id,
            job_title=data.get("job_title"),
            job_location=data.get("job_location"),
            job_description=data.get("job_description"),
            min_gpa=data.get("min_gpa"),
            min_experience=data.get("min_experience"),
            max_experience=data.get("max_experience"),
            degree_requirements=data.get("degree_requirements"),
            requirements_json=data.get("requirements"),
        )

        db.session.add(job)
        db.session.commit()

        return jsonify({"message": "Job created successfully", "job_id": job.id}), 201

    except Exception as e:
        db.session.rollback()  # rollback in case commit failed
        return jsonify({"error": "Failed to create job", "details": str(e)}), 500


@hr_bp.route("/test", methods=["GET"])
def test_connection():
    return jsonify({"status": "success", "message": "Success ✅"}), 200
