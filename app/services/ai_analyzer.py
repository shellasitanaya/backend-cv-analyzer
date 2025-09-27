# Kita butuh spaCy untuk Natural Language Processing (NLP) dan Scikit-learn untuk machine learning.

import spacy
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pprint # Untuk print dictionary dengan rapi saat testing

# Muat model bahasa Inggris dari spaCy
# Lakukan ini di luar fungsi agar model hanya dimuat sekali
try:
    nlp = spacy.load('en_core_web_sm')
except OSError:
    print("Model 'en_core_web_sm' tidak ditemukan. Jalankan 'python -m spacy download en_core_web_sm'")
    nlp = None

# Daftar sederhana kata kunci skill untuk dicari
SKILL_KEYWORDS = [
    'python', 'java', 'c++', 'javascript', 'react', 'reactjs', 'node.js', 'nodejs',
    'flask', 'django', 'spring boot', 'html', 'css', 'tailwind',
    'sql', 'mysql', 'postgresql', 'mongodb', 'database',
    'docker', 'git', 'aws', 'api', 'rest api', 'machine learning',
    'data analysis', 'data science', 'business intelligence', 'seo',
    'digital marketing', 'content marketing', 'sem', 'google analytics'
]

def parse_candidate_info(text):
    """
    Mengekstrak informasi terstruktur dari teks CV mentah.

    Args:
        text (str): Teks lengkap dari CV.

    Returns:
        dict: Dictionary berisi informasi yang diekstrak.
    """
    if not nlp:
        return {"error": "Model spaCy tidak dimuat."}

    # Ubah semua teks menjadi huruf kecil untuk memudahkan pencarian
    text_lower = text.lower()
    
    # Gunakan spaCy untuk memproses teks
    doc = nlp(text)
    
    # --- Ekstraksi Informasi ---
    extracted_data = {
        "name": None,
        "email": None,
        "phone": None,
        "skills": []
    }

    # 1. Ekstraksi Nama menggunakan NER (Named Entity Recognition)
    for ent in doc.ents:
        if ent.label_ == 'PERSON' and not extracted_data['name']:
            extracted_data['name'] = ent.text
            break # Ambil nama orang pertama yang ditemukan

    # 2. Ekstraksi Email menggunakan Regex
    match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    if match:
        extracted_data['email'] = match.group(0)

    # 3. Ekstraksi Nomor Telepon menggunakan Regex
    # Pola ini mencoba menangkap berbagai format nomor telepon Indonesia
    match = re.search(r'(\+62|0)8[1-9][0-9]{7,10}\b', text)
    if match:
        extracted_data['phone'] = match.group(0)
        
    # 4. Ekstraksi Skills menggunakan Keyword Matching
    found_skills = set()
    for keyword in SKILL_KEYWORDS:
        if keyword in text_lower:
            found_skills.add(keyword.title()) # Simpan dengan huruf kapital di awal
    extracted_data['skills'] = list(found_skills)

    return extracted_data

def calculate_match_score(cv_text, job_desc_text):
    """
    Menghitung skor kecocokan antara teks CV dan deskripsi pekerjaan.

    Args:
        cv_text (str): Teks lengkap dari CV.
        job_desc_text (str): Teks lengkap dari deskripsi pekerjaan.

    Returns:
        float: Skor kecocokan dalam bentuk persentase (0-100).
    """
    if not cv_text or not job_desc_text:
        return 0.0

    # Gabungkan kedua teks ke dalam satu list untuk dianalisis
    documents = [cv_text, job_desc_text]

    # Buat objek TF-IDF Vectorizer
    # stop_words='english' akan menghapus kata umum dalam bahasa Inggris
    tfidf = TfidfVectorizer(stop_words='english')

    # Hitung matriks TF-IDF
    tfidf_matrix = tfidf.fit_transform(documents)

    # Hitung cosine similarity antara vektor pertama (CV) dan vektor kedua (Job Desc)
    cosine_sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])

    # Skor adalah nilai di dalam matriks hasil (misal: [[0.85]])
    score = cosine_sim[0][0]

    # Ubah menjadi persentase dan bulatkan 2 angka di belakang koma
    return round(score * 100, 2)

# =================================================================
# BAGIAN UNTUK TESTING
# =================================================================
if __name__ == '__main__':
    # Contoh teks CV untuk diuji
    sample_cv_text = """
    Budi Santoso
    A passionate software engineer based in Jakarta.
    Email: budi.santoso@email.com, Phone: +6281234567890

    Experience:
    - Software Developer at PT. Cipta Solusi (2022 - Present)
      Developed a web application using Python and Flask.
      Managed SQL database and created REST API.
    
    Skills:
    - Programming: Java, Python, JavaScript
    - Frameworks: ReactJS, Flask
    - Databases: MySQL
    """
    
    print("--- Menguji Fungsi Parsing Info Kandidat ---")
    parsed_info = parse_candidate_info(sample_cv_text)
    
    print("Hasil Parsing:")
    pprint.pprint(parsed_info)

    print("\n" + "="*30 + "\n")
    
    # --- Tambahkan bagian tes untuk fungsi scoring ---
    print("--- Menguji Fungsi Scoring Kecocokan ---")
    sample_job_description = """
    We are hiring a Python Developer.
    Must have experience with Flask framework and REST API development.
    Knowledge of SQL is required. ReactJS is a plus.
    """

    score = calculate_match_score(sample_cv_text, sample_job_description)
    print(f"Teks CV:\n{sample_cv_text[:100]}...")
    print(f"\nDeskripsi Pekerjaan:\n{sample_job_description[:100]}...")
    print(f"\nSKOR KECOCOKAN: {score}%")