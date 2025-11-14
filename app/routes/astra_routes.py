from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
from app.services.astra_scoring_service import AstraScoringService
from app.services.cv_parser import extract_text
from app.services.ai_analyzer import parse_candidate_info, fallback_parse_candidate_info
import traceback

astra_bp = Blueprint('astra_api', __name__, url_prefix='/api/astra')

# Folder sementara untuk upload CV
UPLOAD_FOLDER = 'temp_uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@astra_bp.route('/jobs', methods=['GET'])
def get_astra_jobs():
    """Get daftar lowongan Astra yang tersedia"""
    try:
        job_descriptions = AstraScoringService.get_job_descriptions()
        return jsonify({
            "status": "success",
            "data": job_descriptions
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Gagal mengambil data lowongan: {str(e)}"
        }), 500

@astra_bp.route('/analyze/<job_type>', methods=['POST'])
def analyze_cv_for_astra_job(job_type):
    """
    Analisis CV untuk lowongan Astra tertentu
    job_type: 'erp_business_analyst' atau 'it_data_engineer'
    """
    print(f"🔍 [ASTRA DEBUG] Memulai analisis CV untuk job: {job_type}")
    
    # Validasi job type
    if job_type not in ['erp_business_analyst', 'it_data_engineer']:
        return jsonify({
            "status": "error",
            "message": "Job type tidak valid. Pilih: erp_business_analyst atau it_data_engineer"
        }), 400

    # Validasi file
    if 'cv_file' not in request.files:
        return jsonify({
            "status": "error", 
            "message": "File CV tidak ditemukan"
        }), 400

    cv_file = request.files['cv_file']
    if cv_file.filename == '':
        return jsonify({
            "status": "error",
            "message": "Nama file CV tidak boleh kosong"
        }), 400

    # Proses file
    filename = secure_filename(cv_file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    try:
        # Save file sementara
        cv_file.save(file_path)
        print(f"✅ [ASTRA DEBUG] File disimpan: {file_path}")

        # Extract text dari CV
        cv_text = extract_text(file_path)
        if not cv_text:
            return jsonify({
                "status": "error",
                "message": "Tidak dapat mengekstrak teks dari file CV"
            }), 400

        print(f"✅ [ASTRA DEBUG] Teks diekstrak: {len(cv_text)} karakter")

        # Parsing info kandidat dengan fallback
        try:
            parsed_info = parse_candidate_info(cv_text)
            print("✅ [ASTRA DEBUG] Parsing dengan BERT NER berhasil")
        except Exception as parse_error:
            print(f"⚠️ [ASTRA DEBUG] Parsing BERT gagal, menggunakan fallback: {parse_error}")
            parsed_info = fallback_parse_candidate_info(cv_text)
            print("✅ [ASTRA DEBUG] Parsing fallback berhasil")

        # Analisis CV menggunakan service Astra
        analysis_result = AstraScoringService.analyze_cv_for_job(cv_text, job_type)

        # Format response
        job_info = AstraScoringService.get_job_descriptions()[job_type]
        
        response_data = {
            "status": "success",
            "job_info": job_info,
            "analysis_result": analysis_result,
            "parsed_info": parsed_info
        }

        print(f"✅ [ASTRA DEBUG] Analisis berhasil. Skor: {analysis_result.get('skor_akhir', 0)}")
        return jsonify(response_data), 200

    except Exception as e:
        print(f"❌ [ASTRA DEBUG] Error analisis CV: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            "status": "error",
            "message": f"Terjadi kesalahan saat menganalisis CV: {str(e)}"
        }), 500

    finally:
        # Cleanup file sementara
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"🧹 [ASTRA DEBUG] File sementara dihapus: {file_path}")

@astra_bp.route('/analyze-text/<job_type>', methods=['POST'])
def analyze_cv_text_for_astra_job(job_type):
    """
    Analisis CV dari teks (tanpa upload file) untuk lowongan Astra
    """
    # Validasi job type
    if job_type not in ['erp_business_analyst', 'it_data_engineer']:
        return jsonify({
            "status": "error",
            "message": "Job type tidak valid. Pilih: erp_business_analyst atau it_data_engineer"
        }), 400

    # Validasi input
    data = request.get_json()
    if not data or 'cv_text' not in data:
        return jsonify({
            "status": "error",
            "message": "Data CV text tidak ditemukan"
        }), 400

    cv_text = data['cv_text']
    if not cv_text.strip():
        return jsonify({
            "status": "error", 
            "message": "Teks CV tidak boleh kosong"
        }), 400

    try:
        # Analisis CV menggunakan service Astra
        analysis_result = AstraScoringService.analyze_cv_for_job(cv_text, job_type)

        # Format response
        job_info = AstraScoringService.get_job_descriptions()[job_type]
        
        response_data = {
            "status": "success", 
            "job_info": job_info,
            "analysis_result": analysis_result
        }

        return jsonify(response_data), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Terjadi kesalahan saat menganalisis CV: {str(e)}"
        }), 500