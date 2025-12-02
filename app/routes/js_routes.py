# app/routes/js_routes.py
from flask import Blueprint, request, jsonify
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

UPLOAD_FOLDER = 'temp_uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

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
        
        # [FIX] Real Word Count
        real_word_count = len(cv_text.split())
        keyword_results['total_words'] = real_word_count

        # 3. Simpan CV
        cv_id = str(uuid.uuid4())
        perm_folder = f"user_uploads/{current_user_id}"
        os.makedirs(perm_folder, exist_ok=True)
        perm_path = f"{perm_folder}/{cv_id}_{filename}"
        
        shutil.move(temp_path, perm_path)

        new_cv = CV(
            id=cv_id,
            user_id=current_user_id,
            cv_title=cv_title,
            original_filename=filename,
            storage_path=perm_path,
            uploaded_at=datetime.utcnow()
        )
        db.session.add(new_cv)

        # 4. Simpan Analysis (FIX ERROR DISINI)
        # ==========================================
        analysis_id = str(uuid.uuid4())  # <--- INI YANG KURANG TADI
        # ==========================================
        
        full_job_desc_stored = f"{job_title_input}\n\n{job_description_text}"

        new_analysis = Analysis(
            id=analysis_id, # Pakai variabel yang sudah didefinisikan
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
            "analysis_id": analysis_id, # Sekarang variabel ini dikenali
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

# (Sisa endpoint GET/DELETE di bawahnya biarkan sama, tidak ada yang berubah logicnya)
# Copy paste dari file sebelumnya jika perlu, atau biarkan saja kalau Anda sudah punya
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

@js_bp.route('/cv/<cv_id>', methods=['DELETE'])
@jwt_required()
def delete_cv(cv_id):
    cv = CV.query.get(cv_id)
    if cv:
        if os.path.exists(cv.storage_path):
            os.remove(cv.storage_path)
        db.session.delete(cv)
        db.session.commit()
        return jsonify({"status": "success"}), 200
    return jsonify({"error": "Not found"}), 404