# app/routes/js_routes.py
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
import shutil  # Gunakan shutil untuk memindahkan file
import re
from flask_jwt_extended import jwt_required, get_jwt_identity
# scoring and analysis imports
from app.services.cv_parser import extract_text
from app.services.ai_analyzer import check_ats_friendliness, analyze_keywords
from app.services.astra_scoring_service import AstraScoringService
from app.models import CV, Analysis
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
# ENDPOINT UNTUK ANALISIS CV & SIMPAN KE DATABASE - FIXED VERSION
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
    job_description_key = request.form.get('job_description', '') # Ini adalah 'erp_business_analyst' atau 'it_data_engineer'
    cv_title = request.form.get('cv_title', 'Untitled CV')

    if cv_file.filename == '':
        return jsonify({"error": "File CV tidak boleh kosong"}), 400
    if not job_description_key:
        return jsonify({"error": "Job description key tidak boleh kosong"}), 400

    # 2. Dapatkan user ID dari JWT
    current_user_id = get_jwt_identity()

    # 3. Proses File - Simpan ke LOKASI TEMPORER
    filename = secure_filename(cv_file.filename)
    # Buat nama file unik sementara untuk menghindari konflik
    temp_filename = f"{uuid.uuid4()}_{filename}"
    temp_file_path = os.path.join(UPLOAD_FOLDER, temp_filename)

    # Dapatkan deskripsi pekerjaan lengkap dari AstraService
    job_descriptions = AstraScoringService.get_job_descriptions()
    current_job_info = job_descriptions.get(job_description_key)

    if not current_job_info:
        return jsonify({"error": f"Job key '{job_description_key}' tidak valid"}), 400
    
    # Gabungkan semua teks deskripsi untuk analisis
    job_desc_full_text = f"{current_job_info['nama']} {current_job_info['deskripsi']} {' '.join(current_job_info['job_requirements'])}"

    try:
        # === PERBAIKAN #1: Simpan file HANYA SEKALI ke folder temp ===
        cv_file.save(temp_file_path)

        # 4. Ekstrak Teks dari CV
        cv_text = extract_text(temp_file_path)
        if not cv_text:
            raise ValueError("Teks tidak dapat diekstrak dari file CV.")

        print(f"📄 CV Text extracted: {len(cv_text)} characters")
        print(f"🎯 Job key: {job_description_key}")

        # 5. PANGGIL ASTRA SCORING SERVICE
        astra_scoring_result = None
        final_score = 0
        
        try:
            print("🔄 Memanggil AstraScoringService...")
            # Ini sekarang akan memanggil parse_candidate_info yang sudah diperbaiki
            astra_scoring_result = AstraScoringService.analyze_cv_for_job(cv_text, job_description_key)
            print(f"✅ Astra Scoring Result: {astra_scoring_result}")
            
            if astra_scoring_result.get('lulus', False):
                final_score = astra_scoring_result['skor_akhir']
            else:
                final_score = astra_scoring_result.get('skor_akhir', 0) # Tetap tampilkan skor walau tidak lulus
                
        except Exception as e:
            print(f"❌ Astra Scoring failed: {str(e)}")
            # Fallback jika Astra service error
            final_score = 0
            astra_scoring_result = {
                "lulus": False,
                "skor_akhir": 0,
                "alasan": [f"Astra service error: {str(e)}"],
                "detail_skor": {},
                "parsed_info": {}
            }

        # 7. Panggil fungsi analisis lainnya (ATS & Keywords)
        #    INI SEKARANG AKAN MEMANGGIL FUNGSI YANG SUDAH DIPERBAIKI
        ats_results = check_ats_friendliness(cv_text) 
        keyword_results = analyze_keywords(cv_text, job_desc_full_text, job_type=job_description_key)

        # 8. Tentukan Path Penyimpanan Permanen
        cv_id = str(uuid.uuid4())
        permanent_storage_path = f"user_uploads/{current_user_id}/{cv_id}_{filename}"
        os.makedirs(os.path.dirname(permanent_storage_path), exist_ok=True)
        
        # === PERBAIKAN #2: Pindahkan file dari temp ke permanen ===
        shutil.move(temp_file_path, permanent_storage_path)
        print(f"✅ File dipindahkan ke: {permanent_storage_path}")

        # 9. Simpan CV ke database
        new_cv = CV(
            id=cv_id,
            user_id=current_user_id,
            cv_title=cv_title,
            original_filename=filename,
            storage_path=permanent_storage_path, # Simpan path permanen
            uploaded_at=datetime.utcnow()
        )
        db.session.add(new_cv)

        # 10. Simpan hasil analisis ke database
        analysis_id = str(uuid.uuid4())
        new_analysis = Analysis(
            id=analysis_id,
            cv_id=cv_id,
            job_description_text=job_desc_full_text, # Simpan teks lengkap
            match_score=final_score,
            ats_check_result_json=ats_results, # Simpan hasil ATS yang baru
            keyword_analysis_json=keyword_results,
            phrasing_suggestions_json={ 
                "astra_scoring_detail": astra_scoring_result 
            },
            analyzed_at=datetime.utcnow()
        )
        db.session.add(new_analysis)
        
        # === PERBAIKAN #3: Commit ke database ===
        db.session.commit()
        print(f"✅ CV {cv_id} dan Analisis {analysis_id} berhasil disimpan ke DB.")

        # 11. Format response - SESUAIKAN DENGAN FRONTEND AnalysisResults.jsx
        analysis_result = {
            "analysis_id": analysis_id,
            "cv_id": cv_id,
            "match_score": final_score,
            "job_info": current_job_info, # Kirim info pekerjaan lengkap
            "ats_friendliness": ats_results, # Kirim hasil ATS baru
            "keyword_analysis": keyword_results,
            "parsed_info": astra_scoring_result.get('parsed_info', {}),
            "astra_scoring_detail": astra_scoring_result,
            "requirements_check": {
                "passed": astra_scoring_result.get('lulus', False),
                "reasons": astra_scoring_result.get('alasan', [])
            },
            "message": "Analisis berhasil dan disimpan ke database."
        }

        print(f"📤 Sending response with score: {final_score}%")
        return jsonify(analysis_result), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ [ROUTE] Error in analyze_cv: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Terjadi kesalahan: {str(e)}"}), 500
    finally:
        # 12. Hapus file sementara JIKA MASIH ADA
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            print(f"🗑️ File sementara {temp_file_path} dihapus.")

# =================================================================
# ENDPOINT UNTUK MENDAPATKAN HISTORY CV USER
# =================================================================
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
                    "match_score": float(analysis.match_score) if analysis.match_score is not None else 0,
                    "analyzed_at": analysis.analyzed_at.isoformat() if analysis.analyzed_at else None,
                    "job_description_preview": (analysis.job_description_text or "No Description")[:100] + "..."
                }
            
            result.append(cv_data)

        return jsonify({
            "status": "success",
            "data": result,
            "count": len(result)
        }), 200

    except Exception as e:
        print(f"❌ Error in get_my_cvs: {str(e)}")
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
        
        job_name_match = re.search(r"^(.*?) - ", analysis.job_description_text)
        job_name = job_name_match.group(1) if job_name_match else "Analysis"

        astra_details = (analysis.phrasing_suggestions_json or {}).get('astra_scoring_detail', {})
        parsed_info = astra_details.get('parsed_info', {})
        
        job_descriptions = AstraScoringService.get_job_descriptions()
        job_info_from_astra = job_descriptions.get(astra_details.get('job_type'), {})
        if not job_info_from_astra and 'job_info' in astra_details:
             job_info_from_astra = astra_details.get('job_info', {})


        analysis_data = {
            "analysis_id": analysis.id,
            "cv_id": analysis.cv_id,
            "job_description": analysis.job_description_text,
            "match_score": float(analysis.match_score) if analysis.match_score is not None else 0,
            "ats_friendliness": analysis.ats_check_result_json or {},
            "keyword_analysis": analysis.keyword_analysis_json or {},
            "analyzed_at": analysis.analyzed_at.isoformat() if analysis.analyzed_at else None,
            
            "job_info": {
                "nama": job_info_from_astra.get('nama', job_name),
                "description": job_info_from_astra.get('deskripsi', analysis.job_description_text),
                "requirements": job_info_from_astra.get('requirements_wajib', '')
            },
            "parsed_info": parsed_info,
            "astra_scoring_detail": astra_details,
            "requirements_check": {
                "passed": astra_details.get('lulus', False),
                "reasons": astra_details.get('alasan', [])
            }
        }

        return jsonify({
            "status": "success",
            "data": analysis_data
        }), 200

    except Exception as e:
        print(f"❌ Error in get_analysis_detail: {str(e)}")
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
    try:
        current_user_id = get_jwt_identity()
        cv = CV.query.filter_by(id=cv_id, user_id=current_user_id).first()
        
        if not cv:
            return jsonify({
                "status": "error",
                "message": "CV tidak ditemukan"
            }), 404

        if cv.storage_path and os.path.exists(cv.storage_path):
            os.remove(cv.storage_path)

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