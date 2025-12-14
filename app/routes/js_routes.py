# app/routes/js_routes.py
from flask import Blueprint, request, jsonify, send_file
from flask_cors import cross_origin
from werkzeug.utils import secure_filename
import os
import shutil
import uuid
from datetime import datetime
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.services.cv_parser import extract_text
from app.services.ai_analyzer import check_ats_friendliness, analyze_keywords
from app.services.astra_scoring_service import AstraScoringService 
from app.models import CV, Analysis
from app.extensions import db

js_bp = Blueprint('jobseeker_api', __name__, url_prefix='/api/jobseeker')

# --- [CRITICAL FIX] PATH CONFIGURATION ---
# File ini ada di: .../backend-cv-analyzer/app/routes/js_routes.py

current_file_path = os.path.abspath(__file__)                # .../app/routes/js_routes.py
routes_dir = os.path.dirname(current_file_path)              # .../app/routes
app_dir = os.path.dirname(routes_dir)                        # .../app
PROJECT_ROOT = os.path.dirname(app_dir)                      # .../backend-cv-analyzer (ROOT PROJECT)

# Folder upload sejajar dengan folder 'app'
UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, 'temp_uploads')
PERMANENT_UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, 'user_uploads')

# Pastikan folder ada
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(PERMANENT_UPLOAD_FOLDER):
    os.makedirs(PERMANENT_UPLOAD_FOLDER)

print(f"📂 Project Root detected at: {PROJECT_ROOT}")
print(f"📂 User Uploads target: {PERMANENT_UPLOAD_FOLDER}")


# --- 1. ENDPOINT ANALISIS CV ---
@js_bp.route('/analyze', methods=['POST'])
@jwt_required()
def analyze_cv():
    if 'cv_file' not in request.files:
        return jsonify({"error": "File CV tidak ditemukan"}), 400

    cv_file = request.files['cv_file']
    job_description_text = request.form.get('job_description', '') 
    job_title_input = request.form.get('job_title_input', 'Custom Job Position')
    cv_title = request.form.get('cv_title', 'Untitled CV')

    if cv_file.filename == '':
        return jsonify({"error": "File kosong"}), 400
        
    if not job_description_text or len(job_description_text) < 10:
        return jsonify({"error": "Harap masukkan deskripsi pekerjaan (Job Description) yang valid."}), 400

    current_user_id = get_jwt_identity()
    filename = secure_filename(cv_file.filename)
    
    # Simpan Sementara
    temp_filename = f"{uuid.uuid4()}_{filename}"
    temp_path = os.path.join(UPLOAD_FOLDER, temp_filename)

    try:
        cv_file.save(temp_path)
        cv_text = extract_text(temp_path)
        
        if not cv_text or len(cv_text) < 50:
            raise ValueError("CV kosong atau tidak terbaca (Scan Image/Corrupt).")

        # 1. Gemini Analysis
        gemini_result = AstraScoringService.analyze_cv_with_gemini(
            cv_text=cv_text, 
            job_desc_text=job_description_text,
            job_title=job_title_input
        )
        
        if gemini_result.get('error'):
             raise ValueError(f"Gemini Error: {gemini_result['error']}")

        # 2. Pendukung Analysis
        ats_results = check_ats_friendliness(cv_text)
        keyword_results = analyze_keywords(cv_text, job_description_text)
        keyword_results['total_words'] = len(cv_text.split())

        # 3. Pindahkan ke Folder Permanen (user_uploads/uid/...)
        cv_id = str(uuid.uuid4())
        
        # Buat folder khusus user di dalam user_uploads
        user_folder_path = os.path.join(PERMANENT_UPLOAD_FOLDER, str(current_user_id))
        if not os.path.exists(user_folder_path):
            os.makedirs(user_folder_path)
            
        # Path tujuan (Absolut di server)
        final_file_path = os.path.join(user_folder_path, f"{cv_id}_{filename}")
        
        # Pindahkan file
        shutil.move(temp_path, final_file_path)

        # Path Relatif untuk disimpan di Database (Agar bersih)
        # Format: user_uploads/uid/file.pdf
        db_relative_path = os.path.join('user_uploads', str(current_user_id), f"{cv_id}_{filename}")

        new_cv = CV(
            id=cv_id,
            user_id=current_user_id,
            cv_title=cv_title,
            original_filename=filename,
            storage_path=db_relative_path, # Simpan path relatif
            uploaded_at=datetime.utcnow()
        )
        db.session.add(new_cv)

        # 4. Simpan Analysis
        analysis_id = str(uuid.uuid4())
        full_job_desc_stored = f"{job_title_input}\n\n{job_description_text}"

        new_analysis = Analysis(
            id=analysis_id,
            cv_id=cv_id,
            job_description_text=full_job_desc_stored,
            match_score=gemini_result.get('skor_akhir', 0),
            ats_check_result_json=ats_results, 
            keyword_analysis_json=keyword_results, 
            phrasing_suggestions_json=gemini_result.get('ai_analysis', {}),
            analyzed_at=datetime.utcnow()
        )
        db.session.add(new_analysis)
        db.session.commit()

        return jsonify({
            "status": "success",
            "analysis_id": analysis_id,
            "match_score": gemini_result.get('skor_akhir', 0),
            "gemini_result": gemini_result,
            "keyword_analysis": keyword_results,
            "job_info": gemini_result.get('job_info', {})
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error Analysis Route: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# --- 2. ENDPOINT PREVIEW CV ---
@js_bp.route('/cv/preview/<cv_id>', methods=['GET'])
@cross_origin()
@jwt_required()
def preview_cv(cv_id):
    current_user_id = get_jwt_identity()
    
    cv = CV.query.filter_by(id=cv_id, user_id=current_user_id).first()
    
    if not cv:
        return jsonify({"error": "Data CV tidak ditemukan di database."}), 404

    # --- LOGIKA PENCARIAN FILE ---
    # Database menyimpan: 'user_uploads/uid/file.pdf'
    # Kita gabung dengan PROJECT_ROOT: 'C:/.../backend/user_uploads/uid/file.pdf'
    
    full_path = os.path.join(PROJECT_ROOT, cv.storage_path)

    # Debugging: Cetak path yang dicari ke terminal server
    print(f"🔍 REQUEST PREVIEW: Mencari file di: {full_path}")

    if not os.path.exists(full_path):
        # Fallback: Coba cari tanpa folder user_uploads (jika di DB sudah absolute atau salah format)
        fallback_path = os.path.join(PROJECT_ROOT, 'user_uploads', os.path.basename(cv.storage_path))
        if os.path.exists(fallback_path):
            full_path = fallback_path
        else:
            print(f"❌ GAGAL: File fisik tidak ditemukan.")
            return jsonify({"error": "File fisik tidak ditemukan di server.", "path_searched": full_path}), 404

    mimetype = 'application/pdf'
    lower_filename = cv.original_filename.lower()
    
    if lower_filename.endswith('.docx'):
        mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    elif lower_filename.endswith('.doc'):
        mimetype = 'application/msword'
    
    response = send_file(
        full_path,
        mimetype=mimetype,
        as_attachment=False, 
        download_name=cv.original_filename
    )
    # Cache control agar browser tidak menyimpan versi lama
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


# --- 3. ENDPOINT GET HISTORY ---
@js_bp.route('/my-cvs', methods=['GET'])
@jwt_required()
def get_my_cvs():
    try:
        current_user_id = get_jwt_identity()
        latest_analysis_sq = db.session.query(
            Analysis.cv_id,
            db.func.max(Analysis.analyzed_at).label('latest_analyzed_at')
        ).group_by(Analysis.cv_id).subquery()

        cvs_with_analyses = db.session.query(CV, Analysis).\
            outerjoin(latest_analysis_sq, CV.id == latest_analysis_sq.c.cv_id).\
            outerjoin(Analysis, db.and_(
                Analysis.cv_id == latest_analysis_sq.c.cv_id,
                Analysis.analyzed_at == latest_analysis_sq.c.latest_analyzed_at
            )).\
            filter(CV.user_id == current_user_id).\
            order_by(CV.uploaded_at.desc()).all()

        result = []
        for cv, analysis in cvs_with_analyses:
            job_preview = "Unknown Job"
            if analysis and analysis.job_description_text:
                job_preview = analysis.job_description_text.split('\n')[0][:50]

            result.append({
                "cv_id": cv.id,
                "cv_title": cv.cv_title,
                "original_filename": cv.original_filename,
                "uploaded_at": cv.uploaded_at.isoformat(),
                "latest_analysis": {
                    "analysis_id": analysis.id,
                    "match_score": float(analysis.match_score),
                    "job_description": job_preview
                } if analysis else None
            })
        return jsonify({"status": "success", "data": result}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# --- 4. ENDPOINT GET DETAIL ---
@js_bp.route('/analysis/<analysis_id>', methods=['GET'])
@jwt_required()
def get_analysis_detail(analysis_id):
    try:
        analysis = Analysis.query.filter_by(id=analysis_id).first()
        if not analysis: return jsonify({"status": "error"}), 404
        
        gemini_data = analysis.phrasing_suggestions_json or {}
        keyword_data = analysis.keyword_analysis_json or {}
        
        return jsonify({
            "status": "success",
            "data": {
                "match_score": float(analysis.match_score),
                "gemini_result": {"ai_analysis": gemini_data},
                "keyword_analysis": keyword_data,
                "ats_friendliness": analysis.ats_check_result_json,
                "job_description": analysis.job_description_text
            }
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# --- 5. ENDPOINT DELETE ---
@js_bp.route('/cv/<cv_id>', methods=['DELETE'])
@jwt_required()
def delete_cv(cv_id):
    cv = CV.query.get(cv_id)
    if cv:
        # Hapus file fisik
        full_path = os.path.join(PROJECT_ROOT, cv.storage_path)
        if os.path.exists(full_path):
            os.remove(full_path)
            
        db.session.delete(cv)
        db.session.commit()
        return jsonify({"status": "success"}), 200
    return jsonify({"error": "Not found"}), 404