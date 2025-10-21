import spacy
import re
import pprint
import datetime
import warnings
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from spacy.language import Language
from typing import List, Dict, Union

try:
    from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
    import torch
    warnings.filterwarnings("ignore", "Some weights of the model were not initialized")
except ImportError:
    print("ERROR: Pustaka 'transformers' atau 'torch' tidak ditemukan. Harap install dengan 'pip install transformers torch'")

# Inisialisasi NER Pipeline menggunakan BERT Indonesia
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
    print(f"--- Model NER Indonesia '{model_name}' (Hugging Face) berhasil dimuat. ---")
except Exception as e:
    print(f"ERROR: Gagal memuat model NER Indonesia: {e}")

# # Daftar kata kunci skill untuk dicari
SKILL_KEYWORDS = [
    'python', 'java', 'c++', 'javascript', 'react', 'reactjs', 'node.js', 'nodejs',
    'flask', 'django', 'spring boot', 'html', 'css', 'tailwind',
    'sql', 'mysql', 'postgresql', 'mongodb', 'database',
    'docker', 'git', 'aws', 'api', 'rest api', 'machine learning',
    'data analysis', 'data science', 'business intelligence', 'seo',
    'digital marketing', 'content marketing', 'sem', 'google analytics'
]


def normalize_name(name: str) -> str:
    """Normalisasi nama: kapitalisasi tiap kata, kecuali singkatan full uppercase."""
    if not name:
        return None
    words = name.split()
    normalized_words = []
    for w in words:
        if w.isupper():
            normalized_words.append(w)
        else:
            normalized_words.append(w.capitalize())
    return " ".join(normalized_words)


def extract_name_with_fallback(text):
    # cari baris sebelum email
    lines = text.strip().splitlines()
    for i, line in enumerate(lines):
        if re.search(r'@', line) or re.search(r'\d{9,}', line):  # baris email/phone
            if i > 0:
                candidate = lines[i-1].strip()
                # pastikan bukan "Member of..." atau kata teknis
                if (len(candidate.split()) >= 2 and 
                    not re.search(r'(Member|Division|Tech Stack|github|linkedin)', candidate, re.IGNORECASE)):
                    return candidate
    return None

def parse_candidate_info(text, required_skills=[]):
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
        pattern_without_keyword = r'([0-4][.,]\d+)\s*\/\s*4[.,]0+'
        gpa_match = re.search(pattern_without_keyword, text_lower)

    if gpa_match:
        gpa_string = gpa_match.group(gpa_match.lastindex)
        gpa_string_standard = gpa_string.replace(',', '.')
        extracted_data['gpa'] = float(gpa_string_standard)
        
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


def calculate_match_score(cv_text, job_desc_text):
    """Menghitung skor kecocokan antara teks CV dan deskripsi pekerjaan."""
    if not cv_text or not job_desc_text: return 0.0
    # Stop words tetap menggunakan 'english' karena TfidfVectorizer tidak memiliki stop words bawaan bahasa Indonesia
    documents = [cv_text, job_desc_text]
    tfidf = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf.fit_transform(documents)
    cosine_sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
    score = cosine_sim[0][0]
    return round(score * 100, 2)
    
# --- TESTING ---
if __name__ == '__main__':
    # Teks CV yang sama untuk diuji
    sample_cv_text = """
    CHARLES WIJAYA

Member of Information System Department
BEM (Badan Eksekutif Mahasiswa) is an organization dedicated to fostering the growth of students at Petra Christian
University and overseeing extracurricular activities within PCU. I am honored to have been entrusted with the role of member
of Information Systems within the BEM organization. Our mission, within the Information Systems department, is to develop
systems that facilitate both internal and external activities of the organization. For instance, this involves creating websites to
streamline bureaucratic processes within our university and enhancing administrative tasks within the organization.The
Information Systems team within BEM will be utilizing frameworks for both backend and frontend development, specifically
Laravel and ReactJS.

081938363287 | charleswijaya04@gmail.com | https://www.linkedin.com/in/charles-wijaya-653955285/

Dukuh Kupang Timur XV / 60

I am a Data Science and Analytics student at Petra Christian University with expertise in data analysis, machine
learning, and software development. I have experience in processing, analyzing, and visualizing data using
programming languages such as Python, SQL, and R. Additionally, I have experience in application development
using backend frameworks like Laravel and Node.js, as well as frontend frameworks like React, Vue.js, Tailwind,
and Bootstrap. I am passionate about continuously learning and developing innovative solutions in the fields of
data and technology.

Informatics Rally Games and Logic 2023
Feb 2023 - Nov 2023

Member of IT Game Division
Informatics Rally Games and Logic 2023, a dynamic competition where participants have the chance to play and enjoy a
variety of games developed by students. In this event, students have created and developed their own games using platforms
like Unity, showcasing their creativity and technical skills. As a contributor to this initiative, I have developed one of the featured games,   
focusing on delivering an engaging and innovative gaming experience.

Work Experiences

Petra Christian University
Jul 2023 - Present

Assistant Lecturer
I am deeply appreciative of the chance to serve as an Assistant Lecturer at Petra Christian University. In this role, I have
actively contributed by supporting faculty members in teaching students who face difficulties in certain subjects. By providing
additional guidance, I aim to help students overcome their challenges and enhance their understanding of the material. This
collaborative effort not only supports the teaching staff but also enriches the students' learning experience, ultimately
contributing to their academic success.

Petra Christian University
Jul 2024 - Present

Lab Assistant
I work as a lab assistant at Universitas Kristen Petra, where my primary responsibilities include managing the laboratory and handling
administrative tasks to support academic activities. In this role, I ensure that all lab equipment functions properly and is ready for use,      
while also helping maintain a conducive learning environment. Additionally, I assist lecturers with administrative tasks such as preparing       
course materials, tracking student attendance, and assisting in report preparation. Through this role, I have developed skills in
management, coordination, and improving operational efficiency in the lab.

Education Level

UK Petra - Jl. Siwalankerto No.121-131, Siwalankerto, Kec. Wonocolo, Surabaya,
Jawa Timur 60236

Jul 2022 - Jul 2026 (Expected)

Bachelor Degree in Petra Christian University, 3.97/4.00
    """
    
    print("\n--- Menguji Fungsi Parsing Info dengan Model NER Indonesia (BERT) ---")
    parsed_info = parse_candidate_info(sample_cv_text)
    
    print("\nHasil Parsing:")
    pprint.pprint(parsed_info)

    from typing import Dict, List, Union

# Muat model bahasa Inggris dari spaCy - pindahkan ke bagian atas sebelum fungsi
try:
    nlp: Language = spacy.load('en_core_web_sm')
except OSError:
    print("Model 'en_core_web_sm' tidak ditemukan. Jalankan 'python -m spacy download en_core_web_sm'")
    nlp = None

# Daftar sederhana kata kunci skill untuk dicari
SKILL_KEYWORDS: List[str] = [
    'python', 'java', 'c++', 'javascript', 'react', 'reactjs', 'node.js', 'nodejs',
    'flask', 'django', 'spring boot', 'html', 'css', 'tailwind',
    'sql', 'mysql', 'postgresql', 'mongodb', 'database',
    'docker', 'git', 'aws', 'api', 'rest api', 'machine learning',
    'data analysis', 'data science', 'business intelligence', 'seo',
    'digital marketing', 'content marketing', 'sem', 'google analytics'
]

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
            "experience": "pengalaman kerja" in text_lower or "experience" in text_lower,
            "education": "pendidikan" in text_lower or "education" in text_lower,
            "skills": "keterampilan" in text_lower or "skills" in text_lower
        },
        "contact_info": {
            "email_found": bool(re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)),
            "phone_found": bool(re.search(r'(\+62|0)8[1-9][0-9]{7,10}\b', text))
        },
        "file_format_notes": [
            "Pastikan file tidak menggunakan format dua kolom.",
            "Hindari penggunaan gambar, grafik, atau ikon yang berlebihan."
        ]
    }

def analyze_keywords(cv_text: str, job_desc_text: str) -> Dict[str, Union[List[str], str]]:
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
        token.text.lower() for token in doc 
        if token.pos_ in ['NOUN', 'PROPN'] 
        and len(token.text) > 2 
        and token.text.lower() not in ['experience', 'knowledge', 'responsibilities', 'requirements']
    }
    
    # Menambahkan skill dari daftar jika ada di deskripsi pekerjaan
    job_keywords.update(skill for skill in SKILL_KEYWORDS if skill in job_desc_text.lower())

    matched_keywords = sorted({kw for kw in job_keywords if kw in cv_text_lower})
    missing_keywords = sorted({kw for kw in job_keywords if kw not in cv_text_lower})

    return {
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords
    }

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