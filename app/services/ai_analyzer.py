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
import google.generativeai as genai


try:
    from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
    import torch
except ImportError:
    print("ERROR: transformers/torch missing. Install via: pip install transformers torch")
    pass

# ===============================================
# IMPORT NEW SERVICE
# ===============================================
try:
    from app.services.astra_scoring_service import AstraScoringService
except ImportError:
    print("⚠️ WARNING: Could not import AstraScoringService")

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
api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
    print("--- Gemini configured. ---")
else:
    print("ERROR: GEMINI_API_KEY not found in .env")

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

# Skill keywords (for fallback mode)
SKILL_KEYWORDS = [
    'python', 'java', 'c++', 'javascript', 'react', 'reactjs', 'node.js', 'nodejs',
    'flask', 'django', 'spring boot', 'html', 'css', 'tailwind',
    'sql', 'mysql', 'postgresql', 'mongodb', 'database',
    'docker', 'git', 'aws', 'api', 'rest api', 'machine learning',
    'data analysis', 'data science', 'business intelligence', 'seo',
    'digital marketing', 'content marketing', 'sem', 'google analytics'
]


# ===============================================
# 2. UTILITY FUNCTIONS (Fallback Parser)
# ===============================================

def normalize_name(name: str) -> str:
    if not name:
        return None
    words = name.split()
    output = []
    for w in words:
        if w.isupper():
            output.append(w)
        else:
            output.append(w.capitalize())
    return " ".join(output)

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
# 3. PARSING LOGIC
# ===============================================

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

    json_schema = {
        "name": "Candidate's full name (string)",
        "email": "Candidate's email (string, null if not found)",
        "phone": "Candidate's phone number (string, null if not found)",
        "gpa": "GPA as a float value (float, null if not found)",
        "education": "Education level and major (string, e.g., 'Bachelor of Computer Science', null if not found)",
        "skills": ["skill 1", "skill 2"], 
        "experience": ["Role at Company (Date Start - Date End)"], 
        "total_experience": 0 
    }
    
    # Prompt
    prompt = f"""
    You are a highly meticulous AI HR Assistant. Your task is to extract structured information from the following CV text.
    Return the answer ONLY in valid JSON format, WITHOUT additional text, markdown formatting, or explanations at the beginning or end.
    
    STRICT JSON SCHEMA TO FOLLOW:
    {json.dumps(json_schema, indent=2)}
    
    CRITICAL INSTRUCTIONS:
    1. **name**: Extract the candidate's full name.
    2. **gpa**: Find the GPA/IPK and convert it to a float (e.g., 3.37). If not found, return null.
    3. **education**: Extract the highest education level AND major (string, e.g., 'Bachelor of Computer Science', 'Diploma in IT', 'Master of Business'). If not found, return null.
    4. **skills**: Extract ALL skills (technical hard skills and soft skills) found in the CV. Return as a list of strings. Example: ["Python", "SQL", "Tableau", "Leadership", "Communication"].
    5. **experience**: Extract each work experience as ONE string per job entry. Combine the Job Title, Company Name (if available), and Date Range. Example: ["Business Analyst at Google (May 2023–NOW)", "Data Analyst at Startup Inc (May 2022–May 2023)"].
    6. **total_experience**: Calculate the total number of years of professional experience. 
       - Logic: Determine the earliest start date of their career and the latest end date. Calculate the span (Latest - Earliest).
       - Do NOT simply sum up the duration of overlapping jobs.
       - Use the current year as 'NOW' or 'PRESENT'.
       - Return as a SINGLE INTEGER (round to the nearest year).
    7. **Null Handling**: If a field is not found in the text, return null (except for 'skills' and 'experience', return []). DO NOT add new fields outside the schema.
    
    Here is the CV Text:
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

    short_text = " ".join(text.split()[:100])
    ner_results = NER_INDONESIA_PIPELINE(short_text)

    print("\n--- [DEBUG] Semua Entitas PERSON (PER) yang Ditemukan BERT NER ---")
    all_person_entities = []
    for ent in ner_results:
        if ent['entity_group'] == 'PER':
            word = ent['word'].replace(' ##', '').replace('##', '').strip()
            all_person_entities.append(word)
    print(all_person_entities)
    print("----------------------------------------------------")

    best_name = None
    if all_person_entities:
        best_name = max(all_person_entities, key=len)
        if len(best_name.split()) == 1 and not best_name.isupper():
            best_name = None

    # Fallback regex (ambil first line kalau masuk akal)
    if not best_name:
        lines = text.strip().splitlines()
        if lines:
            first_line = lines[0].strip()
            if not re.search(r'@|\d|https?://', first_line):
                best_name = first_line
            elif first_line.isupper() and len(first_line.split()) >= 2:
                best_name = first_line

    # Fallback tambahan (cari baris sebelum email/phone)
    if not best_name:
        best_name = extract_name_with_fallback(text)

    #  Normalisasi akhir
    extracted_data['name'] = normalize_name(best_name)

    text_lower = text.lower()
    if any(keyword in text_lower for keyword in ['s2', 'master', 'magister']):
        extracted_data['education'] = 'S2'
    elif any(keyword in text_lower for keyword in ['s1', 'bachelor', 'sarjana']):
        extracted_data['education'] = 'S1'
    elif any(keyword in text_lower for keyword in ['d3', 'diploma']):
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
    
    gpa_match = None
    pattern_with_keyword = r'(gpa|ipk)\s*:?\s*([0-4][.,]\d+)'
    gpa_match = re.search(pattern_with_keyword, text_lower)

    if not gpa_match:
        pattern_slash_4 = r'([0-4][.,]\d+)\s*\/\s*4[.,]0+'
        gpa_match = re.search(pattern_slash_4, text_lower)

    if not gpa_match:
        pattern_slash_any = r'([0-4][.,]\d+)\s*\/\s*([0-4][.,]\d+)'
        gpa_match = re.search(pattern_slash_any, text_lower)

    if gpa_match:
        try:
            gpa_string = gpa_match.group(1)  # ✅ ALWAYS take first number
            gpa_string_standard = gpa_string.replace(',', '.')
            extracted_data['gpa'] = float(gpa_string_standard)
            print(f"✅ [GPA EXTRACTION] Found GPA: {extracted_data['gpa']}")
        except (ValueError, IndexError) as e:
            print(f"⚠️ [GPA EXTRACTION] Failed to parse: {e}")
            extracted_data['gpa'] = 0.0
    else:
        print(f"⚠️ [GPA EXTRACTION] No GPA pattern found in CV")
        extracted_data['gpa'] = 0.0
        
    year_ranges = re.findall(r'(\d{4})\s*-\s*(\d{4}|present|sekarang)', text, re.IGNORECASE)
    total_years = 0
    current_year = datetime.datetime.now().year
    
    # pengalaman BELOMM
    for start_year, end_year in year_ranges:
        try:
            start = int(start_year)
            end = current_year if end_year.lower() in ['present', 'sekarang'] else int(end_year)
            duration = end - start
            # Hanya tambahkan durasi yang masuk akal sebagai pengalaman (misalnya 1 hingga 10 tahun)
            if 0 < duration <= 10: total_years += duration
        except ValueError: continue
    
    # Mencari total tahun pengalaman secara eksplisit
    if total_years == 0:
        exp_match = re.search(r'(\d+)\s*\+?\s*(tahun|years)\s*pengalaman', text_lower)
        if exp_match: total_years = int(exp_match.group(1))
        
    # Memberikan batas atas yang wajar agar hasilnya tidak terlalu tinggi
    extracted_data['experience'] = min(total_years, 15) 

    return extracted_data


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

# ===============================================
# 5. AI SEMANTIC MATCH SCORING
# ===============================================

def get_best_available_model():
    """
    Mendeteksi model terbaik yang tersedia di akun Google AI Studio Anda
    berdasarkan urutan prioritas yang diinginkan.
    """
    priority_list = [
        'models/gemini-2.5-flash', 
        'models/gemini-2.0-flash', 
        'models/gemini-1.5-pro',
        'models/gemini-1.5-flash', 
        'models/gemini-pro'
    ]
    
    try:
        # Ambil daftar model yang aktif dan support 'generateContent'
        available_models = [
            m.name for m in genai.list_models() 
            if 'generateContent' in m.supported_generation_methods
        ]
        
        # Cek satu per satu dari priority list
        for model_name in priority_list:
            if model_name in available_models:
                print(f"[SYSTEM] Model terpilih: {model_name}")
                return model_name
                
        # Jika tidak ada yang cocok di priority list, ambil yang pertama tersedia
        return available_models[0] if available_models else 'models/gemini-1.5-flash'
        
    except Exception as e:
        print(f"[WARNING] Gagal list_models ({e}), fallback ke gemini-1.5-flash")
        return 'models/gemini-1.5-flash'
    
def get_ai_match_score(cv_text, job_description_text):
    """
    Menghitung match score menggunakan AI (Gemini) untuk perbandingan semantik.
    Ini jauh lebih akurat daripada TF-IDF.
    """
    
    model_name = get_best_available_model() 
    gemini_model = None 
    
    try:
        gemini_model = genai.GenerativeModel(model_name)
    except Exception as e:
        print(f"ERROR: Tidak bisa memuat model {model_name}: {e}")
        return {"match_score": 0, "reasoning": "Model AI Error."}

    # Skema JSON yang kita inginkan sebagai output dari AI
    json_schema = {
        "match_score": 0, # Angka 0-100
        "reasoning": "Penjelasan singkat mengapa skornya segitu (pro & cons)",
        "matched_skills": ["Skill 1", "Skill 2"],
        "missing_skills": ["Skill 3", "Skill 4"]
    }
    
    # Prompt 
    prompt = f"""
    Act as a Senior Head of Talent Acquisition with 20+ years of experience.
    Your task is to evaluate a candidate's CV against a Job Description (JD) using a STRICT SCORING RUBRIC.
    
    You must output ONLY valid JSON format, no preamble or markdown formatting.

    === INPUT DATA ===
    
    [CANDIDATE CV]:
    {cv_text}
    
    [JOB DESCRIPTION]:
    {job_description_text}

    === SCORING RUBRIC (TOTAL: 100 POINTS) ===
    You must calculate the score based strictly on these 3 dimensions:

    1. HARD SKILLS & RELEVANCE (Weight: 60% -> Max 60 Points)
       - Does the candidate possess the MANDATORY technical skills required in the JD?
       - Is the work experience relevance to the industry?
       - Context Logic: If JD requires "Python" and CV only shows "Python Course" (no real work), score this lower.
       - Synonym Logic: "Team Lead" in CV matches "Manager" in JD.

    2. SENIORITY & EXPERIENCE (Weight: 20% -> Max 20 Points)
       - Does the candidate meet the minimum years of experience?
       - Is the seniority level (Junior/Mid/Senior) appropriate?

    3. DESCRIPTION QUALITY & IMPACT (Weight: 20% -> Max 20 Points)
       - ACTION VERBS: Award points if CV uses strong verbs (e.g., "Developed", "Spearheaded", "Optimized") instead of passive ones ("Responsible for").
       - QUANTITATIVE RESULTS: Award BONUS points if CV contains numbers/metrics (e.g., "Increased sales by 20%", "Reduced latency by 2s").
       - If the CV is generic with no numbers/impact, score this section LOW (0-10 points).

    === INSTRUCTIONS ===
    1. Analyze the CV against the JD.
    2. Calculate the score for each of the 3 rubric sections above.
    3. Sum them up to get the final `match_score`.
    4. In the `reasoning` field, briefly explain the pros/cons based on these 3 criteria (e.g., "High skill match, but low score on description quality due to lack of metrics").
    5. List `matched_skills` and `missing_skills`.

    === JSON OUTPUT FORMAT ===
    {json.dumps(json_schema)}
    """

    try:
        print(f"[DEBUG] Memanggil API Gemini untuk SCORING...")
        generation_config = genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.2
        )
        response = gemini_model.generate_content(prompt, generation_config=generation_config)
        
        parsed_data = json.loads(response.text)
        return parsed_data

    except Exception as e:
        print(f"ERROR: Gagal memanggil API scoring Gemini: {e}")
        return {"score": 0, "reasoning": f"Gagal parsing: {e}"}


# ===============================================
# 6. ATS CHECK
# ===============================================
def check_ats_friendliness(text: str):
    text_lower = text.lower()
    return {
        "common_sections": {
            "experience": "experience" in text_lower or "pengalaman" in text_lower,
            "education": "education" in text_lower or "pendidikan" in text_lower,
            "skills": "skills" in text_lower or "keterampilan" in text_lower,
        },
        "contact_info": {
            "email_found": bool(re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text)),
            "phone_found": bool(re.search(r"(\+62|0)8[1-9][0-9]{7,10}\b", text)),
        },
        "file_format_notes": [
            "Jangan gunakan dua kolom.",
            "Hindari gambar atau ikon.",
        ],
    }


# ===============================================
# 7. KEYWORD ANALYSIS
# ===============================================
def analyze_keywords(cv_text: str, jd_text: str):
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(jd_text)
    cv_lower = cv_text.lower()

    keywords = {
        token.text.lower()
        for token in doc 
        if token.pos_ in ["NOUN", "PROPN"] and len(token.text) > 2
    }

    # Add skill keywords
    keywords.update([s for s in SKILL_KEYWORDS if s in jd_text.lower()])

    matched = sorted([kw for kw in keywords if kw in cv_lower])
    missing = sorted([kw for kw in keywords if kw not in cv_lower])

    return {"matched_keywords": matched, "missing_keywords": missing}

def fallback_parse_candidate_info(text):
    """
    Fallback parsing function ketika BERT NER gagal.
    Menggunakan regex dan rule-based approach.
    """
    print("🔄 Using fallback candidate info parsing...")
    
    extracted_data = {
        "name": None, 
        "email": None, 
        "phone": None, 
        "gpa": None,
        "experience": 0, 
        "skills": [], 
        "education": None,
        "language": "id"  # Default language
    }

    # Email extraction
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    if email_match:
        extracted_data['email'] = email_match.group(0)

    # Phone extraction
    phone_match = re.search(r'(\+62|62|0)8[1-9][0-9]{7,10}\b', text)
    if phone_match:
        extracted_data['phone'] = phone_match.group(0)

    # Name extraction fallback - cari di baris pertama yang reasonable
    lines = text.strip().splitlines()
    for line in lines:
        line_clean = line.strip()
        # Skip jika line mengandung email, phone, atau URL
        if (re.search(r'@|\d{9,}|http', line_clean) or 
            len(line_clean) < 3 or 
            len(line_clean) > 100):
            continue
            
        # Jika line terlihat seperti nama (2-4 kata, kapitalisasi proper)
        words = line_clean.split()
        if 2 <= len(words) <= 4 and any(word.istitle() for word in words):
            extracted_data['name'] = line_clean
            break

    # Education level detection
    text_lower = text.lower()
    if any(keyword in text_lower for keyword in ['s2', 'master', 'magister']):
        extracted_data['education'] = 'S2'
    elif any(keyword in text_lower for keyword in ['s1', 'bachelor', 'sarjana']):
        extracted_data['education'] = 'S1'
    elif any(keyword in text_lower for keyword in ['d3', 'diploma']):
        extracted_data['education'] = 'D3'

    # GPA extraction
    gpa_match = None
    pattern_with_keyword = r'(gpa|ipk)\s*:?\s*([0-4][.,]\d+)'
    gpa_match = re.search(pattern_with_keyword, text_lower)

    if not gpa_match:
        pattern_without_keyword = r'([0-4][.,]\d+)\s*\/\s*4[.,]0+'
        gpa_match = re.search(pattern_without_keyword, text_lower)

    if gpa_match:
        gpa_string = gpa_match.group(gpa_match.lastindex)
        gpa_string_standard = gpa_string.replace(',', '.')
        extracted_data['gpa'] = float(gpa_string_standard)

    # Language detection sederhana
    english_words = ['the', 'and', 'of', 'to', 'a', 'in', 'is', 'you', 'are', 'for']
    id_words = ['dan', 'dengan', 'dari', 'untuk', 'pada', 'yang', 'di', 'ke', 'ini', 'itu']
    
    english_count = sum(1 for word in english_words if word in text_lower)
    indonesian_count = sum(1 for word in id_words if word in text_lower)
    
    if english_count > indonesian_count:
        extracted_data['language'] = 'en'
    elif indonesian_count > english_count:
        extracted_data['language'] = 'id'
    else:
        extracted_data['language'] = 'mixed'

    print(f"✅ Fallback parsing completed - Language: {extracted_data['language']}")
    return extracted_data