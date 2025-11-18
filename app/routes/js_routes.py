from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
from flask_jwt_extended import jwt_required, get_jwt_identity
# scoring and analysis imports
from app.services.cv_parser import extract_text
from app.services.ai_analyzer import calculate_match_score, check_ats_friendliness, analyze_keywords
from app.models import CV, Analysis, User
from app.extensions import db
import uuid
from datetime import datetime

# Prefix /api/jobseeker akan digunakan untuk semua rute di file ini
js_bp = Blueprint('jobseeker_api', __name__, url_prefix='/api/jobseeker')

# Folder sementara untuk menyimpan CV yang diunggah
UPLOAD_FOLDER = 'temp_uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# =================================================================
# ENDPOINT UNTUK ANALISIS CV & SIMPAN KE DATABASE
# =================================================================
@js_bp.route('/analyze', methods=['POST'])
@jwt_required()
def analyze_cv():
    """
    Endpoint untuk menganalisis CV yang diunggah terhadap deskripsi pekerjaan.
    Menyimpan CV dan hasil analisis ke database.
    """
    # 1. Validasi Input
    if 'cv_file' not in request.files:
        return jsonify({"error": "File CV (cv_file) tidak ditemukan"}), 400

    cv_file = request.files['cv_file']
    job_description = request.form.get('job_description', '')
    cv_title = request.form.get('cv_title', 'Untitled CV')

    if cv_file.filename == '':
        return jsonify({"error": "File CV tidak boleh kosong"}), 400

    # 2. Dapatkan user ID dari JWT
    current_user_id = get_jwt_identity()

    # 3. Proses File
    filename = secure_filename(cv_file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    try:
        cv_file.save(file_path)

        # 4. Ekstrak Teks dari CV
        cv_text = extract_text(file_path)
        if not cv_text:
            raise ValueError("Teks tidak dapat diekstrak dari file CV.")

        # 5. Panggil semua fungsi analisis dari ai_analyzer.py
        score = calculate_match_score(cv_text, job_description)
        ats_results = check_ats_friendliness(cv_text)
        keyword_results = analyze_keywords(cv_text, job_description)

        # 6. Simpan CV ke database
        cv_id = str(uuid.uuid4())
        storage_path = f"user_uploads/{current_user_id}/{cv_id}_{filename}"
        
        # Buat direktori jika belum ada
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)
        
        # Pindahkan file ke storage permanen
        cv_file.save(storage_path)

        new_cv = CV(
            id=cv_id,
            user_id=current_user_id,
            cv_title=cv_title,
            original_filename=filename,
            storage_path=storage_path,
            uploaded_at=datetime.utcnow()
        )
        db.session.add(new_cv)

        # 7. Simpan hasil analisis ke database
        analysis_id = str(uuid.uuid4())
        new_analysis = Analysis(
            id=analysis_id,
            cv_id=cv_id,
            job_description_text=job_description,
            match_score=score,
            ats_check_result_json=ats_results,
            keyword_analysis_json=keyword_results,
            analyzed_at=datetime.utcnow()
        )
        db.session.add(new_analysis)
        db.session.commit()

        # 8. Format response
        analysis_result = {
            "analysis_id": analysis_id,
            "cv_id": cv_id,
            "match_score": score,
            "ats_friendliness": ats_results,
            "keyword_analysis": keyword_results,
            "message": "Analisis berhasil dan disimpan ke database."
        }

        return jsonify(analysis_result), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Terjadi kesalahan: {str(e)}"}), 500
    finally:
        # 9. Hapus file sementara setelah selesai
        if os.path.exists(file_path):
            os.remove(file_path)

# =================================================================
# ENDPOINT UNTUK MENDAPATKAN HISTORY CV USER
# =================================================================
@js_bp.route('/my-cvs', methods=['GET'])
@jwt_required()
def get_my_cvs():
    """
    Endpoint untuk mendapatkan semua CV dan analisis milik user
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Query semua CV user beserta analisis terbaru
        cvs_with_analyses = db.session.query(CV, Analysis).\
            outerjoin(Analysis, CV.id == Analysis.cv_id).\
            filter(CV.user_id == current_user_id).\
            order_by(CV.uploaded_at.desc()).all()

        result = []
        for cv, analysis in cvs_with_analyses:
            cv_data = {
                "cv_id": cv.id,
                "cv_title": cv.cv_title,
                "original_filename": cv.original_filename,
                "uploaded_at": cv.uploaded_at.isoformat() if cv.uploaded_at else None,
                "latest_analysis": None
            }
            
            if analysis:
                cv_data["latest_analysis"] = {
                    "analysis_id": analysis.id,
                    "match_score": float(analysis.match_score) if analysis.match_score else 0,
                    "analyzed_at": analysis.analyzed_at.isoformat() if analysis.analyzed_at else None,
                    "job_description_preview": analysis.job_description_text[:100] + "..." if analysis.job_description_text else ""
                }
            
            result.append(cv_data)

        return jsonify({
            "status": "success",
            "data": result,
            "count": len(result)
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Gagal mengambil data CV: {str(e)}"
        }), 500

# =================================================================
# ENDPOINT UNTUK MENDAPATKAN DETAIL ANALISIS
# =================================================================
@js_bp.route('/analysis/<analysis_id>', methods=['GET'])
@jwt_required()
def get_analysis_detail(analysis_id):
    """
    Endpoint untuk mendapatkan detail analisis spesifik
    """
    try:
        current_user_id = get_jwt_identity()
        
        analysis = db.session.query(Analysis).\
            join(CV, Analysis.cv_id == CV.id).\
            filter(Analysis.id == analysis_id, CV.user_id == current_user_id).\
            first()

        if not analysis:
            return jsonify({
                "status": "error",
                "message": "Analisis tidak ditemukan"
            }), 404

        analysis_data = {
            "analysis_id": analysis.id,
            "cv_id": analysis.cv_id,
            "job_description": analysis.job_description_text,
            "match_score": float(analysis.match_score) if analysis.match_score else 0,
            "ats_check_result": analysis.ats_check_result_json or {},
            "keyword_analysis": analysis.keyword_analysis_json or {},
            "analyzed_at": analysis.analyzed_at.isoformat() if analysis.analyzed_at else None
        }

        return jsonify({
            "status": "success",
            "data": analysis_data
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Gagal mengambil detail analisis: {str(e)}"
        }), 500

# =================================================================
# ENDPOINT UNTUK MENGHAPUS CV
# =================================================================
@js_bp.route('/cv/<cv_id>', methods=['DELETE'])
@jwt_required()
def delete_cv(cv_id):
    """
    Endpoint untuk menghapus CV dan semua analisis terkait
    """
    try:
        current_user_id = get_jwt_identity()
        
        cv = CV.query.filter_by(id=cv_id, user_id=current_user_id).first()
        
        if not cv:
            return jsonify({
                "status": "error",
                "message": "CV tidak ditemukan"
            }), 404

        # Hapus file dari storage
        if os.path.exists(cv.storage_path):
            os.remove(cv.storage_path)

        # Hapus dari database (cascade akan menghapus analyses juga)
        db.session.delete(cv)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "CV berhasil dihapus"
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": f"Gagal menghapus CV: {str(e)}"
        }), 500