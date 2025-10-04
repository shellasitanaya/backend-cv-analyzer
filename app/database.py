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
# VERSI BARU YANG BENAR
def get_all_candidates_for_job(job_id):
    """
    Mengambil kandidat yang lolos filter untuk sebuah job, 
    termasuk data spesifik dari kolom JSON.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # --- INI BAGIAN UTAMA YANG DIUBAH ---
        query = """
        SELECT 
            id, 
            extracted_name, 
            match_score, 
            status,
            JSON_EXTRACT(structured_profile_json, '$.gpa') AS gpa,
            JSON_EXTRACT(structured_profile_json, '$.experience') AS experience
        FROM Candidates 
        WHERE job_id = %s AND status = 'passed_filter'
        ORDER BY match_score DESC
        """
        
        cursor.execute(query, (job_id,))
        candidates = cursor.fetchall()
        return candidates
        
    except Exception as e:
        print(f"Database error in get_all_candidates_for_job: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def save_candidate(job_id, data):
    """Menyimpan data satu kandidat ke database dengan semua kolom baru."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Query INSERT sekarang mencakup kolom status dan rejection_reason
        query = """
        INSERT INTO Candidates (
            job_id, original_filename, storage_path, extracted_name,
            extracted_email, extracted_phone, match_score, 
            status, rejection_reason, structured_profile_json
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        # Siapkan data structured_profile untuk diubah menjadi string JSON
        # Jika tidak ada, gunakan objek JSON kosong {}
        profile_data = data.get('structured_profile') or {}
        profile_json_string = json.dumps(profile_data)

        # Siapkan semua nilai untuk dimasukkan ke query
        values = (
            job_id,
            data.get('original_filename'),
            data.get('storage_path'),
            data.get('name'), 
            data.get('email'),
            data.get('phone'), 
            data.get('score'), # Akan NULL jika kandidat ditolak -> ga di analisis klo ga masuk kandidat
            data.get('status', 'processing'), # Mengambil status dari data, defaultnya 'processing'
            data.get('rejection_reason'), # Akan berisi alasan jika ditolak
            profile_json_string
        )

        cursor.execute(query, values)
        conn.commit()
        
        last_id = cursor.lastrowid
        return last_id

    except Exception as e:
        print(f"Database error in save_candidate: {e}")
        if conn:
            conn.rollback() # Batalkan transaksi jika terjadi error
        return None

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_all_jobs():
    """Mengambil semua data pekerjaan dari tabel Jobs."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        # dictionary=True membuat hasil query menjadi format dictionary,
        # yang bisa langsung di-jsonify
        cursor = conn.cursor(dictionary=True)
        
        query = "SELECT id, job_title, min_gpa, degree_requirements FROM Jobs ORDER BY created_at DESC"
        cursor.execute(query)
        
        jobs = cursor.fetchall()
        return jobs
        
    except Exception as e:
        print(f"Database error in get_all_jobs: {e}")
        return [] # Kembalikan list kosong jika terjadi error
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# File: backend/app/database.py

# ... (fungsi lainnya) ...
def get_job_by_id(job_id):
    """Mengambil detail satu pekerjaan berdasarkan ID."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Jobs WHERE id = %s", (job_id,))
    job = cursor.fetchone()
    cursor.close()
    conn.close()
    return job