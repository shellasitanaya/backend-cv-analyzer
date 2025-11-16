import spacy
import re
import pprint
import datetime
import warnings
import os
import json
import re
import google.generativeai as genai
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from spacy.language import Language
from typing import List, Dict, Union
from dotenv import load_dotenv


# --- 1. KONFIGURASI MODEL AI (Gemini) ---
load_dotenv()
try:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY tidak ditemukan. Pastikan ada di file .env")
    else:
        genai.configure(api_key=api_key)
        print("--- Model Generatif Google (Gemini) berhasil dikonfigurasi. ---")
except Exception as e:
    print(f"ERROR: Gagal mengkonfigurasi Gemini: {e}")


# --- 2. DAFTAR SKILL (Tidak kita pakai di prompt, tapi tetap di-load) ---
BUSINESS_ANALYST_SKILLS = [
    "Business Process Modeling", "Requirement Gathering", "SAP", "ERP", "SQL", 
    "Finance", "Communication", "Analytical Thinking", "Negotiation", 
    "Stakeholder Management", "Project Management", "Agile", "Scrum",
]
DATA_ENGINEER_SKILLS = [
    "Python", "SQL", "ETL", "Data Warehousing", "Spark", "Airflow", 
    "Problem Solving", "Analytical Thinking", "Data-driven", "AWS", 
    "GCP", "Tableau", "Power BI",
]


# --- 3. FUNGSI PARSING UTAMA (Sekarang menggunakan AI) ---

def parse_candidate_info(cv_text, required_skills=[]):
    """
    Mengekstrak info kandidat menggunakan Model AI (Gemini)
    untuk mendapatkan hasil yang jauh lebih akurat daripada Regex.
    """
    
    # Definisikan model
    try:
        model = genai.GenerativeModel('models/gemini-2.5-flash')
    except Exception as e:
        print(f"ERROR: Tidak bisa memuat model Gemini: {e}")
        return {} 

    # Ini adalah struktur JSON yang WAJIB dipatuhi oleh sisa aplikasi Anda.
    # AI akan kita paksa untuk mengikuti skema ini.
    json_schema = {
        "name": "Nama lengkap kandidat (string)",
        "email": "Email kandidat (string, null jika tidak ada)",
        "phone": "Nomor telepon kandidat (string, null jika tidak ada)",
        "gpa": "IPK sebagai angka float (float, null jika tidak ada)",
        "education": "Tingkat pendidikan (string, misal: S1, S2, null jika tidak ada)",
        # --- PERUBAHAN DI SINI ---
        "skills": ["skill 1", "skill 2"], # List SEMUA skill yang ditemukan di CV (bukan hanya yang cocok)
        # -------------------------
        "experience": ["Jabatan 1 di Perusahaan 1 (Tanggal 1 - Tanggal 2)", "Jabatan 2 (Tanggal 3 - Tanggal 4)"], # List detail pengalaman
        "total_experience": 0 # Total tahun pengalaman sebagai ANGKA INTEGER
    }
    
    # Buat Prompt (Instruksi) untuk AI
    prompt = f"""
    Anda adalah asisten HR AI yang sangat teliti. Tugas Anda adalah mengekstrak informasi dari teks CV berikut.
    Kembalikan jawaban HANYA dalam format JSON yang valid, TANPA teks tambahan di awal atau akhir.
    
    Skema JSON yang WAJIB Anda ikuti:
    {json.dumps(json_schema, indent=2)}
    
    Instruksi Penting:
    1.  **name**: Ekstrak nama lengkap orang tersebut.
    2.  **gpa**: Cari IPK (GPA) dan ubah menjadi float (misal: 3.37). Jika tidak ada, kembalikan null.
    3. **education**": "Tingkat pendidikan DAN jurusan (string, contoh: 'S1 Computer Science', 'D3 Teknik Informatika', null jika tidak ada)",
    
    # --- PERUBAHAN DI SINI ---
    4.  **skills**: Ekstrak SEMUA skill (keahlian teknis atau soft skill) yang Anda temukan di CV. Kembalikan sebagai sebuah list string. Contoh: ["Python", "SQL", "Tableau", "Leadership", "Communication"].
    # -------------------------
    
    5.  **experience**: Ekstrak setiap pengalaman kerja sebagai SATU string per pekerjaan, gabungkan jabatan, perusahaan (jika ada), dan tanggal. Contoh: ["Business Analyst di CV. Nur Cahaya Pratama (May 2023–NOW)", "Data Analyst di UD Bangkit (May 2022–May 2023)"].
    6.  **total_experience**: Hitung total tahun pengalaman kerja. 
        Jika kandidat memiliki banyak pekerjaan yang tumpang tindih. Jangan jumlahkan durasi setiap proyek. 
        Sebaliknya, tentukan tanggal pekerjaan paling awal (contoh: 2005) dan tanggal pekerjaan terakhir (contoh: 2025). 
        Hitung total rentang karirnya (contoh: 2025 - 2005 = 20). 
        Kembalikan sebagai SATU ANGKA INTEGER. Gunakan tahun 2025 sebagai tahun "NOW" atau "PRESENT".
    7.  Jika sebuah field tidak ditemukan, kembalikan null (kecuali untuk 'skills' dan 'experience', kembalikan []). JANGAN tambahkan field di luar skema.
    
    Berikut adalah teks CV-nya:
    ---
    {cv_text}
    ---
    
    JSON Output:
    """

    # 4. Panggil API
    try:
        print(f"[DEBUG] Memanggil API Gemini untuk parsing...")
        # (Konfigurasi untuk memastikan output JSON)
        generation_config = genai.GenerationConfig(
            response_mime_type="application/json"
        )
        response = model.generate_content(prompt, generation_config=generation_config)
        
        # 5. Parse Respon JSON
        parsed_data = json.loads(response.text)
        
        # Pastikan semua key ada untuk menghindari error di backend
        final_data = json_schema.copy()
        final_data.update(parsed_data)
        
        return final_data

    except json.JSONDecodeError as e:
        print(f"ERROR: Gagal mem-parse JSON dari Gemini: {e}")
        print(f"Response mentah: {response.text}")
        return json_schema # Kembalikan skema kosong
    except Exception as e:
        print(f"ERROR: Terjadi kesalahan saat memanggil API Gemini: {e}")
        return json_schema # Kembalikan skema kosong


# --- 4. FUNGSI SCORING (TIDAK BERUBAH) ---
def calculate_match_score(cv_text, job_desc_text):
    """Menghitung skor kecocokan antara teks CV dan deskripsi pekerjaan."""
    if not cv_text or not job_desc_text:
        return 0.0
    
    documents = [cv_text, job_desc_text]
    try:
        tfidf = TfidfVectorizer(stop_words="english")
        tfidf_matrix = tfidf.fit_transform(documents)
        cosine_sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
        score = cosine_sim[0][0]
        return round(score * 100, 2)
    except ValueError as e:
        print(f"Error TfidfVectorizer (mungkin CV kosong): {e}")
        return 0.0




def check_ats_friendliness(text: str) -> Dict[str, Union[Dict[str, bool], List[str]]]:
    """
    Melakukan pengecekan dasar keramahan ATS pada teks CV.

    Args:
        text (str): Teks dari konten CV.

    Returns:
        Dict: Hasil pengecekan ATS.
    """
    text_lower = text.lower()
    return {
        "common_sections": {
            "experience": "pengalaman kerja" in text_lower
            or "experience" in text_lower,
            "education": "pendidikan" in text_lower or "education" in text_lower,
            "skills": "keterampilan" in text_lower or "skills" in text_lower,
        },
        "contact_info": {
            "email_found": bool(
                re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text)
            ),
            "phone_found": bool(re.search(r"(\+62|0)8[1-9][0-9]{7,10}\b", text)),
        },
        "file_format_notes": [
            "Pastikan file tidak menggunakan format dua kolom.",
            "Hindari penggunaan gambar, grafik, atau ikon yang berlebihan.",
        ],
    }


def analyze_keywords(
    cv_text: str, job_desc_text: str
) -> Dict[str, Union[List[str], str]]:
    """
    Menganalisis dan membandingkan kata kunci antara CV dan deskripsi pekerjaan.

    Args:
        cv_text (str): Teks dari konten CV.
        job_desc_text (str): Teks dari deskripsi pekerjaan.

    Returns:
        Dict: Hasil analisis kata kunci.
    """
    if not nlp:
        return {"error": "Model spaCy tidak dimuat"}

    cv_text_lower = cv_text.lower()
    doc = nlp(job_desc_text)

    # Menggunakan set comprehension untuk efisiensi
    job_keywords = {
        token.text.lower()
        for token in doc
        if token.pos_ in ["NOUN", "PROPN"]
        and len(token.text) > 2
        and token.text.lower()
        not in ["experience", "knowledge", "responsibilities", "requirements"]
    }

    # Menambahkan skill dari daftar jika ada di deskripsi pekerjaan
    job_keywords.update(
        skill for skill in SKILL_KEYWORDS if skill in job_desc_text.lower()
    )

    matched_keywords = sorted({kw for kw in job_keywords if kw in cv_text_lower})
    missing_keywords = sorted({kw for kw in job_keywords if kw not in cv_text_lower})

    return {"matched_keywords": matched_keywords, "missing_keywords": missing_keywords}


# if __name__ == '__main__':
#     sample_cv_text = """
#     Budi Santoso
#     A passionate software engineer based in Jakarta.
#     Email: budi.santoso@email.com, Phone: +6281234567890

#     Experience:
#     - Software Developer at PT. Cipta Solusi (2022 - Present)
#       Developed a web application using Python and Flask.
#       Managed SQL database and created REST API.

#     Skills:
#     - Programming: Java, Python, JavaScript
#     - Frameworks: ReactJS, Flask
#     - Databases: MySQL

#     Education:
#     - S1 Teknik Informatika, Universitas Gadjah Mada
#     """

#     sample_job_description = """
#     We are hiring a Python Developer.
#     Must have experience with Flask framework and REST API development.
#     Knowledge of SQL is required. ReactJS is a plus. Docker is nice to have.
#     """

#     print("--- 1. Menguji Fungsi Parsing Info Kandidat ---")
#     pprint.pprint(parse_candidate_info(sample_cv_text))
#     print("\n" + "="*40 + "\n")

#     print("--- 2. Menguji Fungsi Scoring Kecocokan ---")
#     score = calculate_match_score(sample_cv_text, sample_job_description)
#     print(f"SKOR KECOCOKAN: {score}%")
#     print("\n" + "="*40 + "\n")

#     print("--- 3. Menguji Fungsi ATS Check ---")
#     pprint.pprint(check_ats_friendliness(sample_cv_text))
#     print("\n" + "="*40 + "\n")

#     print("--- 4. Menguji Fungsi Analisis Keyword ---")
#     pprint.pprint(analyze_keywords(sample_cv_text, sample_job_description))
#     print("\n" + "="*40 + "\n")
