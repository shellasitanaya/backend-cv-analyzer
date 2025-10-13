import mysql.connector
from flask import current_app
import json
import uuid

def get_db_connection():
    """Membuat koneksi baru ke database."""
    conn = mysql.connector.connect(
        host=current_app.config['DB_HOST'],
        user=current_app.config['DB_USER'],
        password=current_app.config['DB_PASSWORD'],
        database=current_app.config['DB_NAME']
    )
    return conn


def get_all_candidates_for_job(job_id, filters={}):
    """
    Mengambil kandidat yang lolos dengan filter dinamis, 
    termasuk semua data yang dibutuhkan oleh UI ranking.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query_parts = [
            "SELECT",
            "    id, extracted_name, extracted_email, match_score, status,",
            "    JSON_EXTRACT(structured_profile_json, '$.gpa') AS gpa,",
            "    JSON_EXTRACT(structured_profile_json, '$.experience') AS experience,",
            "    JSON_EXTRACT(structured_profile_json, '$.education') AS education,",
            "    JSON_EXTRACT(structured_profile_json, '$.skills') AS skills",
            "FROM Candidates",
            "WHERE job_id = %s AND status = 'passed_filter'"
        ]
        params = [job_id]

        # (Logika filter dinamis Anda bisa ditambahkan di sini jika sudah ada)
        # Contoh:
        # if filters.get('min_gpa'):
        #     query_parts.append("AND JSON_EXTRACT(structured_profile_json, '$.gpa') >= %s")
        #     params.append(float(filters['min_gpa']))
        
        query_parts.append("ORDER BY match_score DESC")
        
        final_query = " ".join(query_parts)
        
        cursor.execute(final_query, tuple(params))
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
        
        candidate_id = str(uuid.uuid4())
        
        query = """
        INSERT INTO Candidates (
            id, job_id, original_filename, storage_path, extracted_name,
            extracted_email, extracted_phone, match_score, 
            status, rejection_reason, structured_profile_json
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        profile_data = data.get('structured_profile') or {}
        profile_json_string = json.dumps(profile_data)

        values = (
            candidate_id,
            job_id,
            data.get('original_filename'),
            data.get('storage_path'),
            data.get('name'), 
            data.get('email'),
            data.get('phone'), 
            data.get('score'), # Akan NULL jika kandidat ditolak -> ga di analisis klo ga masuk kandidat
            data.get('status', 'processing'), # defaultnya 'processing'
            data.get('rejection_reason'), 
            profile_json_string
        )

        cursor.execute(query, values)
        conn.commit()
        
        last_id = cursor.lastrowid
        return last_id

    except Exception as e:
        print(f"Database error in save_candidate: {e}")
        if conn:
            conn.rollback() 
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
        cursor = conn.cursor(dictionary=True)
        
        query = "SELECT id, job_title, min_gpa, degree_requirements FROM Jobs ORDER BY created_at DESC"
        cursor.execute(query)
        
        jobs = cursor.fetchall()
        return jobs
        
    except Exception as e:
        print(f"Database error in get_all_jobs: {e}")
        return [] 
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_job_by_id(job_id):
    """Mengambil detail satu pekerjaan berdasarkan ID."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Jobs WHERE id = %s", (job_id,))
    job = cursor.fetchone()
    cursor.close()
    conn.close()
    return job


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
