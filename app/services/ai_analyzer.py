# app/services/ai_analyzer.py
import spacy
import os
import re
import json
import pprint
import warnings
import datetime
from typing import List, Dict, Union

import spacy
from spacy.language import Language

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from dotenv import load_dotenv

# ------------------------
# Gemini
# ------------------------
import google.generativeai as genai

# ------------------------
# Transformers (NER Indonesia)
# ------------------------
try:
    from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
    import torch
except ImportError:
    print("ERROR: transformers/torch missing. Install via: pip install transformers torch")
    pass

# ===============================================
# 1. INITIALIZATION
# ===============================================

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
    print("--- Gemini configured. ---")
else:
    print("ERROR: GOOGLE_API_KEY not found in .env")

# --- 2. DAFTAR SKILL  ---
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

# Load BERT Indonesian NER
NER_INDONESIA_PIPELINE = None
try:
    model_name = "cahya/bert-base-indonesian-NER"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForTokenClassification.from_pretrained(model_name)
    NER_INDONESIA_PIPELINE = pipeline(
        "ner", 
        model=model,
        tokenizer=tokenizer,
        aggregation_strategy="simple"
    )
    print(f"--- BERT NER Indonesia '{model_name}' loaded. ---")
except Exception as e:
    print(f"ERROR loading NER model: {e}")

# Muat model bahasa Inggris dari spaCy
try:
    nlp: Language = spacy.load('en_core_web_sm')
    print("✅ spaCy model 'en_core_web_sm' berhasil dimuat")
except OSError:
    print("❌ Model 'en_core_web_sm' tidak ditemukan. Jalankan 'python -m spacy download en_core_web_sm'")
    nlp = None

# Daftar kata kunci skill untuk dicari
SKILL_KEYWORDS = [
    'python', 'java', 'c++', 'javascript', 'react', 'reactjs', 'node.js', 'nodejs',
    'flask', 'django', 'spring boot', 'html', 'css', 'tailwind',
    'sql', 'mysql', 'postgresql', 'mongodb', 'database',
    'docker', 'git', 'aws', 'api', 'rest api', 'machine learning',
    'data analysis', 'data science', 'business intelligence', 'seo',
    'digital marketing', 'content marketing', 'sem', 'google analytics'
]

# Job-specific important keywords
JOB_SPECIFIC_KEYWORDS = {
    "erp_business_analyst": [
        "erp", "enterprise resource planning", "business process", "proses bisnis",
        "analytical", "analitis", "requirements", "kebutuhan", "blueprint",
        "bpmn", "uml", "flowchart", "user stories", "stakeholder", "pemangku kepentingan",
        "system analysis", "analisis sistem", "healthcare", "rumah sakit", "hospital",
        "process improvement", "process mapping", "gap analysis", "use cases",
        "functional requirements", "non-functional requirements", "test cases",
        "implementation", "migration", "change management", "training", "documentation"
    ],
    "it_data_engineer": [
        "data pipeline", "pipelines data", "etl", "extract transform load", "data warehouse", "gudang data",
        "sql", "database", "big data", "hadoop", "spark", "kafka", "data lake",
        "data modeling", "pemodelan data", "data quality", "kualitas data", "data governance", "tata kelola data",
        "aws", "azure", "google cloud", "cloud", "redshift", "bigquery", "snowflake",
        "python", "pyspark", "scala", "java", "airflow", "dbt", "tableau", "power bi",
        "data integration", "data processing", "batch processing", "real-time processing"
    ]
}

def normalize_name(name: str) -> str:
    if not name:
        return None
    words = name.split()
    output = []
    for w in words:
        if w.isupper():
            output.append(w)
        else:
            normalized_words.append(w.capitalize())
    return " ".join(normalized_words)

def extract_name_with_fallback(text):
    lines = text.strip().splitlines()
    for i, line in enumerate(lines):
        if re.search(r'@', line) or re.search(r'\d{9,}', line):
            if i > 0:
                candidate = lines[i-1].strip()
                if (len(candidate.split()) >= 2 and 
                    not re.search(r'(Member|Division|Tech Stack|github|linkedin)', candidate, re.IGNORECASE)):
                    return candidate
    return None


# ===============================================
# 3. AI FIRST, THEN FALLBACK PARSER
# ===============================================

# --- 3. FUNGSI PARSING UTAMA (PAKE AI) ---

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
    
def parse_candidate_info_2(text, required_skills=[]):
    """
    Mengekstrak informasi terstruktur:
    - Nama: Menggunakan BERT NER Indonesia.
    - Lainnya: Menggunakan Regex dan Keyword Matching.
    """
    if NER_INDONESIA_PIPELINE is None:
        print("ERROR: Model NER Indonesia tidak dimuat, parsing dibatalkan.")
        return {}
    
    extracted_data = { 
        "name": None, "email": None, "phone": None, "gpa": None, 
        'experience': 0, "skills": [], "education": None
    }
    
    text_lower = text.lower()
    short_text = " ".join(text.split()[:100])
    ner_results = NER_INDONESIA_PIPELINE(short_text)

    # --- (Logika Ekstraksi Nama tidak berubah) ---
    all_person_entities = []
    for ent in ner_results:
        if ent['entity_group'] == 'PER':
            word = ent['word'].replace(' ##', '').replace('##', '').strip()
            all_person_entities.append(word)

    best_name = None
    if all_person_entities:
        best_name = max(all_person_entities, key=len)
        if len(best_name.split()) == 1 and not best_name.isupper():
            best_name = None
    if not best_name:
        lines = text.strip().splitlines()
        if lines:
            first_line = lines[0].strip()
            if not re.search(r'@|\d|https?://', first_line):
                best_name = first_line
            elif first_line.isupper() and len(first_line.split()) >= 2:
                best_name = first_line
    if not best_name:
        best_name = extract_name_with_fallback(text)
    extracted_data['name'] = normalize_name(best_name)
    # --- (Akhir Logika Ekstraksi Nama) ---

    # === Perbaikan Deteksi Edukasi (dari respons sebelumnya, sudah benar) ===
    if re.search(r'\b(s2|master|magister)\b', text_lower):
        extracted_data['education'] = 'S2'
    elif re.search(r'\b(s1|bachelor|sarjana)\b', text_lower):
        extracted_data['education'] = 'S1'
    elif re.search(r'\b(d3|diploma)\b', text_lower):
        extracted_data['education'] = 'D3'
    
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    if email_match: extracted_data['email'] = email_match.group(0)

    phone_match = re.search(r'(\+62|0)8[1-9][0-9]{7,10}\b', text)
    if phone_match: extracted_data['phone'] = phone_match.group(0)
        
    found_skills = set()
    for keyword in required_skills:
        if keyword in text_lower:
            found_skills.add(keyword.title()) 
    extracted_data['skills'] = list(found_skills)
    
    # === Perbaikan Bug GPA (dari respons sebelumnya, sudah benar) ===
    gpa_match = None
    pattern_with_keyword_before = r'(gpa|ipk)\s*:?\s*([0-4][.,]\d+)' 
    gpa_match = re.search(pattern_with_keyword_before, text_lower)
    if not gpa_match:
        pattern_slash_4 = r'([0-4][.,]\d+)\s*\/\s*4([.,]0+)?' 
        gpa_match = re.search(pattern_slash_4, text_lower)
    if not gpa_match:
        pattern_with_keyword_after = r'([0-4][.,]\d+)\s*(gpa|ipk)'
        gpa_match = re.search(pattern_with_keyword_after, text_lower)
    if not gpa_match:
        pattern_slash_any = r'([0-4][.,]\d+)\s*\/\s*([0-4][.,]\d+)' 
        gpa_match = re.search(pattern_slash_any, text_lower)

    if gpa_match:
        try:
            gpa_string = gpa_match.group(1)
            gpa_string_standard = gpa_string.replace(',', '.')
            extracted_data['gpa'] = float(gpa_string_standard)
            print(f"✅ [GPA EXTRACTION] Found GPA: {extracted_data['gpa']}")
        except (ValueError, IndexError) as e:
            print(f"⚠️ [GPA EXTRACTION] Failed to parse GPA: {e}")
            extracted_data['gpa'] = 0.0
    else:
        print(f"⚠️ [GPA EXTRACTION] No GPA pattern found in CV")
        extracted_data['gpa'] = 0.0
    # === Akhir Perbaikan Bug GPA ===
        
    # =================================================================
    # === PERBAIKAN BUG PENGALAMAN (EXPERIENCE) DIMULAI DI SINI ===
    # =================================================================
    total_years_from_dates = 0.0
    total_years_from_summary = 0.0
    current_year = datetime.datetime.now().year
    current_month = datetime.datetime.now().month

    # Pola 1: Mencari format MM/YYYY atau YYYY (dengan - atau ~)
    # Contoh: 08/2024 - Sekarang, 07/2021~07/2022
    date_pattern_dash = r'(\d{1,2}\/)?(\d{4})\s*[-~]\s*(\d{1,2}\/)?(\d{4}|present|sekarang)'
    year_ranges_dash = re.findall(date_pattern_dash, text, re.IGNORECASE)
    
    # Pola 2: Mencari format YYYY Sekarang (tanpa dash)
    # Contoh: 07/2022 Sekarang
    date_pattern_no_dash = r'(\d{1,2}\/)?(\d{4})\s+(present|sekarang)'
    year_ranges_no_dash = re.findall(date_pattern_no_dash, text, re.IGNORECASE)
    
    all_ranges_text = [m.group(0) for m in re.finditer(date_pattern_dash, text, re.IGNORECASE)] + \
                      [m.group(0) for m in re.finditer(date_pattern_no_dash, text, re.IGNORECASE)]
    
    print(f"🔍 [EXPERIENCE] Found {len(all_ranges_text)} date ranges: {all_ranges_text}")

    # Cek agar tanggal PENDIDIKAN tidak ikut terhitung
    education_section_match = re.search(r'\b(education|pendidikan|academic)\b', text_lower)
    experience_section_match = re.search(r'\b(experience|pengalaman|work history)\b', text_lower)
    
    min_start_date = datetime.datetime.now()
    max_end_date = datetime.datetime(1970, 1, 1)
    has_experience = False

    all_ranges = year_ranges_dash + [(*r, r[2]) for r in year_ranges_no_dash]

    for match_obj in re.finditer(date_pattern_dash, text, re.IGNORECASE):
        start_month_str, start_year_str, end_month_str, end_year_str = match_obj.groups()
        
        # JANGAN HITUNG JIKA BERADA DI BAWAH JUDUL "PENDIDIKAN"
        if education_section_match and match_obj.start() > education_section_match.start():
            # Dan JIKA berada DI ATAS JUDUL "PENGALAMAN" (jika ada)
            if experience_section_match and match_obj.start() < experience_section_match.start():
                print(f"ℹ️ [EXPERIENCE] Skipping date range '{match_obj.group(0)}' (found in education section).")
                continue

        try:
            start_year = int(start_year_str)
            start_month = int(start_month_str.replace('/', '')) if start_month_str else 1
            start_date = datetime.datetime(start_year, start_month, 1)
            
            end_year = current_year if end_year_str.lower() in ['present', 'sekarang'] else int(end_year_str)
            end_month = current_month if end_year_str.lower() in ['present', 'sekarang'] else (int(end_month_str.replace('/', '')) if end_month_str else 12)
            end_date = datetime.datetime(end_year, end_month, 1)

            if start_date < min_start_date: min_start_date = start_date
            if end_date > max_end_date: max_end_date = end_date
            has_experience = True
            
        except ValueError:
            continue

    # (Logika untuk Pola 2, jika perlu - CV Annisa tidak punya ini, tapi untuk jaga-jaga)
    for match_obj in re.finditer(date_pattern_no_dash, text, re.IGNORECASE):
        start_month_str, start_year_str, end_year_str = match_obj.groups()
        if education_section_match and match_obj.start() > education_section_match.start():
            if experience_section_match and match_obj.start() < experience_section_match.start():
                print(f"ℹ️ [EXPERIENCE] Skipping date range '{match_obj.group(0)}' (found in education section).")
                continue
        try:
            start_year = int(start_year_str)
            start_month = int(start_month_str.replace('/', '')) if start_month_str else 1
            start_date = datetime.datetime(start_year, start_month, 1)
            end_date = datetime.datetime.now() # Selalu 'sekarang'

            if start_date < min_start_date: min_start_date = start_date
            if end_date > max_end_date: max_end_date = end_date
            has_experience = True
        except ValueError:
            continue
            
    if has_experience:
        # Hitung total durasi dari tanggal paling awal sampai paling akhir
        # (Ini masih bisa salah jika ada gap, tapi lebih baik dari menjumlahkan)
        total_duration_days = (max_end_date - min_start_date).days
        total_years_from_dates = total_duration_days / 365.25
    
    # Pola 3 (Fallback): Mencari "X years of experience" atau "X tahun pengalaman"
    exp_match = re.search(r'(\d+)\s*\+?\s*(tahun|years)\s*(of experience|pengalaman)', text_lower)
    if exp_match:
        total_years_from_summary = int(exp_match.group(1))
        print(f"✅ [EXPERIENCE] Found '{total_years_from_summary} years' from summary text.")

    # Ambil nilai MAKSIMUM dari kedua perhitungan
    total_years = max(total_years_from_dates, total_years_from_summary)
    
    extracted_data['experience'] = int(round(total_years)) # Bulatkan ke integer terdekat
    print(f"📊 [EXPERIENCE] Total calculated experience: {extracted_data['experience']} years")
    # =================================================================
    # === PERBAIKAN BUG PENGALAMAN (EXPERIENCE) SELESAI ===
    # =================================================================

    return extracted_data

def calculate_match_score(cv_text, job_desc_text):
    """Menghitung skor kecocokan antara teks CV dan deskripsi pekerjaan."""
    if not cv_text or not job_desc_text: return 0.0
    documents = [cv_text, job_desc_text]
    tfidf = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf.fit_transform(documents)
    cosine_sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
    score = cosine_sim[0][0]
    return round(score * 100, 2)

def enhanced_analyze_keywords(cv_text: str, job_desc_text: str, job_type: str = None) -> Dict:
    """
    Enhanced keyword analysis dengan job-specific requirements
    """
    if not nlp:
        return {"error": "Model spaCy tidak dimuat"}
    
    cv_text_lower = cv_text.lower()
    job_desc_lower = job_desc_text.lower()
    
    print(f"🔍 [KEYWORD ANALYSIS] Analyzing for job type: {job_type}")
    
    doc = nlp(job_desc_text)
    job_desc_keywords = {
        token.lemma_.lower() for token in doc 
        if token.pos_ in ['NOUN', 'PROPN', 'VERB'] 
        and len(token.text) > 2 
        and not token.is_stop
    }
    
    if job_type and job_type in JOB_SPECIFIC_KEYWORDS:
        job_specific_keys = JOB_SPECIFIC_KEYWORDS[job_type]
        job_desc_keywords.update(job_specific_keys)
        print(f"✅ Added {len(job_specific_keys)} job-specific keywords for {job_type}")
    
    job_desc_keywords.update(skill for skill in SKILL_KEYWORDS if skill in job_desc_lower)
    
    matched_keywords = sorted({kw for kw in job_desc_keywords if kw in cv_text_lower})
    missing_keywords = sorted({kw for kw in job_desc_keywords if kw not in cv_text_lower})
    
    match_percentage = (len(matched_keywords) / len(job_desc_keywords)) * 100 if job_desc_keywords else 0
    
    job_specific_matches = 0
    if job_type and job_type in JOB_SPECIFIC_KEYWORDS:
        job_specific_matches = len([kw for kw in matched_keywords if kw in JOB_SPECIFIC_KEYWORDS[job_type]])
    
    result = {
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords[:15],  # Limit missing keywords
        "total_searched": len(job_desc_keywords),
        "match_percentage": round(match_percentage, 2),
        "job_specific_matches": job_specific_matches,
        "total_words": len(cv_text.split()),
        "skills_found": len([skill for skill in SKILL_KEYWORDS if skill in cv_text_lower])
    }
    
    print(f"📊 [KEYWORD ANALYSIS] Results: {len(matched_keywords)} matched, {len(missing_keywords)} missing, {match_percentage:.1f}% match")
    print(f"🎯 [KEYWORD ANALYSIS] Job-specific matches: {job_specific_matches}")
    
    return result

def analyze_keywords(cv_text: str, job_desc_text: str, job_type: str = None) -> Dict[str, Union[List[str], str]]:
    """
    Menganalisis dan membandingkan kata kunci antara CV dan deskripsi pekerjaan.
    MENGGUNAKAN enhanced_analyze_keywords sebagai default.
    """
    print(f"🔍 [ANALYZE_KEYWORDS] Called with job_type: {job_type}")
    return enhanced_analyze_keywords(cv_text, job_desc_text, job_type)


# === Perbaikan Bug 're.Match' (dari respons sebelumnya, sudah benar) ===
def check_ats_friendliness(text: str) -> Dict[str, Union[Dict[str, bool], List[str], str, int]]:
    """
    Melakukan pengecekan keramahan ATS yang lebih realistis pada teks CV.
    Mengembalikan struktur yang sesuai dengan frontend AnalysisResults.jsx
    """
    text_lower = text.lower()
    
    score = 100
    suggestions = []
    
    # 1. Cek Informasi Kontak
    email_found = bool(re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text))
    phone_found = bool(re.search(r'(\+62|0)8[1-9][0-9]{7,10}\b', text))
    
    contact_info = {"email_found": email_found, "phone_found": phone_found}
    if not email_found or not phone_found:
        score -= 25
        suggestions.append("Informasi kontak (email/telepon) tidak lengkap atau tidak ditemukan.")

    # 2. Cek Bagian/Section Penting
    # FIX: Mengganti any(re.search(...)) dengan bool(re.search(...))
    sections_found = {
        "experience": bool(re.search(r'\b(experience|pengalaman|work history|riwayat pekerjaan)\b', text_lower)),
        "education": bool(re.search(r'\b(education|pendidikan|academic)\b', text_lower)),
        "skills": bool(re.search(r'\b(skills|keterampilan|keahlian|technical skills)\b', text_lower)),
        "summary": bool(re.search(r'\b(summary|ringkasan|profile|profil|objective)\b', text_lower)),
    }
    
    missing_sections = [section for section, found in sections_found.items() if not found]
    if len(missing_sections) > 0:
        score -= (len(missing_sections) * 10) # 10 poin per bagian yang hilang
        suggestions.append(f"Bagian penting tidak ditemukan: {', '.join(missing_sections)}.")
        
    sections_status = "Complete" if len(missing_sections) == 0 else "Incomplete"
    
    # 3. Cek Format & Keterbacaan
    readability = "Good"
    format_check = "Good"
    
    if len(text.split()) < 150:
        readability = "Fair"
        score -= 10
        suggestions.append("CV terlalu singkat. Tambahkan lebih banyak detail.")
    elif len(text.split()) > 1000:
        readability = "Fair"
        score -= 5
        suggestions.append("CV mungkin terlalu panjang (lebih dari 2 halaman). Ringkas jika memungkinkan.")
        
    if text.count('|') > 10 or text.count('\t') > 20:
        format_check = "Needs Improvement"
        score -= 15
        suggestions.append("CV mungkin menggunakan format multi-kolom atau tabel yang sulit dibaca ATS.")

    # 4. Finalisasi Skor
    final_score = max(0, score) # Pastikan skor tidak negatif
    
    return {
        "compatibility_score": final_score,
        "format_check": format_check,
        "readability": readability,
        "sections_status": sections_status,
        "contact_info": contact_info,
        "common_sections": sections_found,
        "suggestions": suggestions
    }
# === Akhir Perbaikan Bug 're.Match' ===

def fallback_parse_candidate_info(text):
    """
    Fallback parsing function ketika BERT NER gagal.
    """
    print("🔄 Using fallback candidate info parsing...")
    
    extracted_data = {
        "name": None, "email": None, "phone": None, "gpa": None,
        "experience": 0, "skills": [], "education": None, "language": "id"
    }

    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    if email_match: extracted_data['email'] = email_match.group(0)

    phone_match = re.search(r'(\+62|62|0)8[1-9][0-9]{7,10}\b', text)
    if phone_match: extracted_data['phone'] = phone_match.group(0)

    lines = text.strip().splitlines()
    for line in lines:
        line_clean = line.strip()
        if (re.search(r'@|\d{9,}|http', line_clean) or len(line_clean) < 3 or len(line_clean) > 100):
            continue
        words = line_clean.split()
        if 2 <= len(words) <= 4 and any(word.istitle() for word in words):
            extracted_data['name'] = line_clean
            break

    text_lower = text.lower()
    # FIX: Gunakan \b di fallback juga
    if re.search(r'\b(s2|master|magister)\b', text_lower):
        extracted_data['education'] = 'S2'
    elif re.search(r'\b(s1|bachelor|sarjana)\b', text_lower):
        extracted_data['education'] = 'S1'
    elif re.search(r'\b(d3|diploma)\b', text_lower):
        extracted_data['education'] = 'D3'

    # FIX: Logika fallback GPA (dari parse_candidate_info utama)
    gpa_match = None
    pattern_with_keyword_before = r'(gpa|ipk)\s*:?\s*([0-4][.,]\d+)' 
    gpa_match = re.search(pattern_with_keyword_before, text_lower)
    if not gpa_match:
        pattern_slash_4 = r'([0-4][.,]\d+)\s*\/\s*4([.,]0+)?' 
        gpa_match = re.search(pattern_slash_4, text_lower)
    if not gpa_match:
        pattern_with_keyword_after = r'([0-4][.,]\d+)\s*(gpa|ipk)'
        gpa_match = re.search(pattern_with_keyword_after, text_lower)
    if not gpa_match:
        pattern_slash_any = r'([0-4][.,]\d+)\s*\/\s*([0-4][.,]\d+)' 
        gpa_match = re.search(pattern_slash_any, text_lower)

    if gpa_match:
        gpa_string = gpa_match.group(1)
        gpa_string_standard = gpa_string.replace(',', '.')
        extracted_data['gpa'] = float(gpa_string_standard)
        
    # FIX: Logika fallback experience (dari parse_candidate_info utama)
    total_years = 0
    date_pattern_dash = r'(\d{1,2}\/)?(\d{4})\s*[-~]\s*(\d{1,2}\/)?(\d{4}|present|sekarang)'
    year_ranges_dash = re.findall(date_pattern_dash, text, re.IGNORECASE)
    date_pattern_no_dash = r'(\d{1,2}\/)?(\d{4})\s+(present|sekarang)'
    year_ranges_no_dash = re.findall(date_pattern_no_dash, text, re.IGNORECASE)
    
    current_year = datetime.datetime.now().year
    current_month = datetime.datetime.now().month
    
    min_start_date = datetime.datetime.now()
    max_end_date = datetime.datetime(1970, 1, 1)
    has_experience = False

    education_section_match = re.search(r'\b(education|pendidikan|academic)\b', text_lower)
    experience_section_match = re.search(r'\b(experience|pengalaman|work history)\b', text_lower)

    for match_obj in re.finditer(date_pattern_dash, text, re.IGNORECASE):
        start_month_str, start_year_str, end_month_str, end_year_str = match_obj.groups()
        if education_section_match and match_obj.start() > education_section_match.start():
            if experience_section_match and match_obj.start() < experience_section_match.start():
                continue
        try:
            start_year = int(start_year_str)
            start_month = int(start_month_str.replace('/', '')) if start_month_str else 1
            start_date = datetime.datetime(start_year, start_month, 1)
            end_year = current_year if end_year_str.lower() in ['present', 'sekarang'] else int(end_year_str)
            end_month = current_month if end_year_str.lower() in ['present', 'sekarang'] else (int(end_month_str.replace('/', '')) if end_month_str else 12)
            end_date = datetime.datetime(end_year, end_month, 1)
            if start_date < min_start_date: min_start_date = start_date
            if end_date > max_end_date: max_end_date = end_date
            has_experience = True
        except ValueError: continue
            
    for match_obj in re.finditer(date_pattern_no_dash, text, re.IGNORECASE):
        start_month_str, start_year_str, end_year_str = match_obj.groups()
        if education_section_match and match_obj.start() > education_section_match.start():
            if experience_section_match and match_obj.start() < experience_section_match.start():
                continue
        try:
            start_year = int(start_year_str)
            start_month = int(start_month_str.replace('/', '')) if start_month_str else 1
            start_date = datetime.datetime(start_year, start_month, 1)
            end_date = datetime.datetime.now()
            if start_date < min_start_date: min_start_date = start_date
            if end_date > max_end_date: max_end_date = end_date
            has_experience = True
        except ValueError: continue
            
    total_years_from_dates = 0.0
    if has_experience:
        total_duration_days = (max_end_date - min_start_date).days
        total_years_from_dates = total_duration_days / 365.25
    
    total_years_from_summary = 0
    exp_match = re.search(r'(\d+)\s*\+?\s*(tahun|years)\s*(of experience|pengalaman)', text_lower)
    if exp_match:
        total_years_from_summary = int(exp_match.group(1))

    total_years = max(total_years_from_dates, total_years_from_summary)
    extracted_data['experience'] = int(round(total_years))


    english_words = ['the', 'and', 'of', 'to', 'a', 'in', 'is', 'you', 'are', 'for']
    id_words = ['dan', 'dengan', 'dari', 'untuk', 'pada', 'yang', 'di', 'ke', 'ini', 'itu']
    
    english_count = sum(1 for word in english_words if word in text_lower)
    indonesian_count = sum(1 for word in id_words if word in text_lower)
    
    if english_count > indonesian_count: extracted_data['language'] = 'en'
    elif indonesian_count > english_count: extracted_data['language'] = 'id'
    else: extracted_data['language'] = 'mixed'

    print(f"✅ Fallback parsing completed - Language: {extracted_data['language']}")
    return extracted_data

# --- TESTING ---
if __name__ == '__main__':
    sample_cv_text = """
    Annisa Selfidianti
    With 3 years of experience as a Business Analyst...
    Sarjana (S1) Information System
    Pendidikan
    2017 - 2021 3.69/4 GPA
    Pengalaman
    08/2024 - Sekarang
    07/2022 Sekarang
    07/2021~07/2022
    My education is great.
    My skills are great.
    My summary is great.
    """
    
    print("--- Testing parse_candidate_info (with ALL fixes) ---")
    parsed = parse_candidate_info(sample_cv_text)
    pprint.pprint(parsed)

    print("\n--- Testing check_ats_friendliness (with any() fix) ---")
    ats_results = check_ats_friendliness(sample_cv_text)
    pprint.pprint(ats_results)