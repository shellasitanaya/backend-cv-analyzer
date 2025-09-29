import mysql.connector
from flask import current_app
import json

def get_db_connection():
    """Membuat koneksi baru ke database."""
    conn = mysql.connector.connect(
        host=current_app.config['DB_HOST'],
        user=current_app.config['DB_USER'],
        password=current_app.config['DB_PASSWORD'],
        database=current_app.config['DB_NAME']
    )
    return conn

# Contoh fungsi untuk mengambil data dari database
def get_all_candidates_for_job(job_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True) # dictionary=True agar hasilnya seperti objek

    query = "SELECT * FROM Candidates WHERE job_id = %s ORDER BY match_score DESC"
    cursor.execute(query, (job_id,))

    candidates = cursor.fetchall()

    cursor.close()
    conn.close()

    return candidates

def save_candidate(job_id, data):
    """Menyimpan data satu kandidat ke database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
    INSERT INTO Candidates (
        job_id, original_filename, storage_path, extracted_name,
        extracted_email, extracted_phone, match_score, structured_profile_json
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    # Ubah dictionary Python menjadi string JSON untuk disimpan di database
    profile_json_string = json.dumps(data.get('structured_profile'))

    values = (
        job_id,
        data.get('original_filename'),
        data.get('storage_path'),
        data.get('name'),
        data.get('email'),
        data.get('phone'),
        data.get('score'),
        profile_json_string
    )

    cursor.execute(query, values)
    conn.commit() # Simpan perubahan ke database
    
    last_id = cursor.lastrowid # Ambil ID dari data yang baru saja dimasukkan
    
    cursor.close()
    conn.close()

    return last_id # Kembalikan ID kandidat baru

def save_generated_cv(original_cv_id: int, data: dict) -> int:
    """Menyimpan data CV yang di-generate ke tabel GeneratedCVs."""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
    INSERT INTO GeneratedCVs (
        original_cv_id, template_name, version_number, storage_path
    ) VALUES (%s, %s, %s, %s)
    """
    
    values = (
        original_cv_id,
        data.get('template_name'),
        data.get('version_number'),
        data.get('storage_path')
    )

    cursor.execute(query, values)
    conn.commit()
    
    last_id = cursor.lastrowid
    
    cursor.close()
    conn.close()

    return last_id

def get_last_cv_version(original_cv_id: int) -> int:
    """Mendapatkan nomor versi terakhir dari sebuah CV original."""
    conn = get_db_connection()
    # dictionary=True agar bisa akses kolom dengan nama, misal: result['max_version']
    cursor = conn.cursor(dictionary=True)

    query = """
    SELECT MAX(version_number) as max_version 
    FROM GeneratedCVs 
    WHERE original_cv_id = %s
    """
    
    cursor.execute(query, (original_cv_id,))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    if result and result['max_version'] is not None:
        return int(result['max_version'])
    
    # Jika belum ada versi sama sekali, kembalikan 0
    return 0
