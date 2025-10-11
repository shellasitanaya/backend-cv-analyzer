from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
import json

from app.services.cv_parser import extract_text
from app.services.ai_analyzer import parse_candidate_info, calculate_match_score
from app import databases
from app.services.talent_search import search_candidates  


hr_bp = Blueprint('hr_api', __name__, url_prefix='/api/hr')

UPLOAD_FOLDER = 'temp_uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@hr_bp.route('/jobs/<job_id>/upload', methods=['POST'])
def upload_and_process_cvs(job_id):
    print("\n" + "="*50)
    print("--- [DEBUG] REQUEST UPLOAD DITERIMA ---")
    print(f"HEADER Content-Type: {request.headers.get('Content-Type')}")
    print(f"REQUEST.FORM (data teks): {request.form}")
    print(f"REQUEST.FILES (data file): {request.files}")
    print("="*50 + "\n")
    
    if 'cv_files' not in request.files or not request.files.getlist('cv_files'):
        print("!!! [ERROR] 'cv_files' tidak ditemukan di request.files !!!")
        return jsonify({"error": "Backend tidak menerima file 'cv_files'"}), 400
    
    cv_files = request.files.getlist('cv_files')
    job = databases.get_job_by_id(job_id)
    if not job:
        return jsonify({"error": "Job ID tidak ditemukan"}), 404
    job_requirements = {'min_gpa': job.get('min_gpa'), 'min_experience': job.get('min_experience')}
    job_description = job.get('job_description', '')
    
    skills_json_string = job.get('skills_json')
    skills_from_job = {}

    if skills_json_string and isinstance(skills_json_string, str):
        skills_from_job = json.loads(skills_json_string)
    elif isinstance(skills_json_string, dict):
        skills_from_job = skills_json_string

    required_skills = (
        skills_from_job.get('hard_skills', []) + 
        skills_from_job.get('soft_skills', []) + 
        skills_from_job.get('optional_skills', [])
    )
   
    required_skills_lower = [skill.lower() for skill in required_skills]

    report = {"passed_count": 0, "rejected_count": 0, "rejection_details": {}}

    for cv_file in cv_files:
        filename = secure_filename(cv_file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        try:
            cv_file.save(file_path)
            cv_text = extract_text(file_path)

            structured_profile = parse_candidate_info(cv_text, required_skills=required_skills_lower)
            
            rejection_reason = None
            
            candidate_gpa = structured_profile.get('gpa')
            candidate_experience = structured_profile.get('total_experience')

            if job_requirements['min_gpa'] and (not candidate_gpa or candidate_gpa < job_requirements['min_gpa']):
                rejection_reason = f"GPA below minimum requirement ({job_requirements['min_gpa']})"

            elif job_requirements.get('min_experience') and (candidate_experience is None or candidate_experience < job_requirements.get('min_experience')):
                rejection_reason = f"Experience below minimum requirement ({job_requirements.get('min_experience')} years)"

            if rejection_reason:
                report['rejected_count'] += 1
                report['rejection_details'][rejection_reason] = report['rejection_details'].get(rejection_reason, 0) + 1
                
                databases.save_candidate(job_id, {
                    'original_filename': filename,
                    'name': structured_profile.get('name'),
                    'email': structured_profile.get('email'),
                    'phone': structured_profile.get('phone'),
                    'structured_profile': structured_profile, 
                    'status': 'rejected', 
                    'storage_path': file_path,
                    'rejection_reason': rejection_reason
                })
            else:
                report['passed_count'] += 1
                score = calculate_match_score(cv_text, job_description)

                databases.save_candidate(job_id, {
                    'original_filename': filename,
                    'name': structured_profile.get('name'),
                    'email': structured_profile.get('email'),
                    'phone': structured_profile.get('phone'),
                    'score': score,
                    'storage_path': file_path,
                    'structured_profile': structured_profile, # Kirim SEMUA hasil parsing
                    'status': 'passed_filter'
                })
        except Exception as e:
            print(f"Error processing {filename}: {e}")
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
    
    return jsonify(report), 200


@hr_bp.route('/jobs/<job_id>/candidates', methods=['GET'])
def get_ranked_candidates(job_id):
    try:
        # Ambil parameter filter dari URL (e.g., ?min_gpa=3.0&skills=React,Python)
        filters = {
            'min_gpa': request.args.get('min_gpa'),
            'min_exp': request.args.get('min_exp'),
            'skills': request.args.get('skills')
        }
        # Hapus filter yang nilainya kosong
        active_filters = {k: v for k, v in filters.items() if v}
        
        candidates = databases.get_all_candidates_for_job(job_id, active_filters)
        return jsonify(candidates)
    except Exception as e:
        return jsonify({"error": f"Gagal mengambil data dari database: {e}"}), 500
    

@hr_bp.route('/candidates/search', methods=['GET'])
def search_candidates_endpoint():
    try:
        keyword = request.args.get('q', '')
        if not keyword:
            return jsonify({
                "status": "success",
                "message": "Keyword kosong, tidak ada hasil",
                "data": []
            }), 200

        results = search_candidates(keyword)

        return jsonify({
            "status": "success",
            "message": f"{len(results)} kandidat ditemukan untuk keyword '{keyword}'",
            "data": results
        }), 200

    except Exception as e:
        print("ERROR search_candidates:", e)
        return jsonify({
            "status": "error",
            "message": "Terjadi kesalahan saat mencari kandidat",
            "data": [],
            "details": str(e)
        }), 500

# Endpoint untuk profil detail (lakukan hal yang sama)
@hr_bp.route('/candidates/<candidate_id>', methods=['GET'])
def get_candidate_detail(candidate_id):
    # Di sini Anda akan membuat fungsi databases.get_candidate_by_id(candidate_id)
    # Untuk sekarang, kita bisa fokus pada daftar ranking dulu.
    pass

@hr_bp.route('/jobs', methods=['GET'])
def get_jobs_list():
    """Endpoint untuk mengambil semua data pekerjaan."""
    try:
        jobs = databases.get_all_jobs()
        return jsonify(jobs)
    except Exception as e:
        return jsonify({"error": "Gagal mengambil daftar pekerjaan", "details": str(e)}), 500

@hr_bp.route('/test', methods=['GET'])
def test_connection():
    return jsonify({
        "status": "success",
        "message": "Success ✅"
    }), 200