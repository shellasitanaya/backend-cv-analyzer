from typing import Dict, List, Union
import spacy
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pprint
from spacy.language import Language

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

def parse_candidate_info(text: str) -> Dict[str, Union[str, List[str], None]]:
    """
    Mengekstrak informasi terstruktur dari teks CV mentah.
    
    Args:
        text (str): Teks lengkap dari CV.
        
    Returns:
        Dict[str, Union[str, List[str], None]]: Dictionary berisi informasi yang diekstrak.
    """
    if not nlp:
        return {"error": "Model spaCy tidak dimuat"}

    text_lower = text.lower()
    doc = nlp(text)
    
    extracted_data: Dict[str, Union[str, List[str], None]] = {
        "name": None,
        "email": None,
        "phone": None,
        "skills": []
    }

    # Ekstraksi Nama menggunakan NER
    for ent in doc.ents:
        if ent.label_ == 'PERSON' and not extracted_data['name']:
            extracted_data['name'] = ent.text
            break

    # Ekstraksi Email
    if email_match := re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text):
        extracted_data['email'] = email_match.group(0)

    # Ekstraksi Nomor Telepon
    if phone_match := re.search(r'(\+62|0)8[1-9][0-9]{7,10}\b', text):
        extracted_data['phone'] = phone_match.group(0)
        
    # Ekstraksi Skills
    found_skills = {keyword.title() for keyword in SKILL_KEYWORDS if keyword in text_lower}
    extracted_data['skills'] = sorted(list(found_skills))

    return extracted_data

def calculate_match_score(cv_text: str, job_desc_text: str) -> float:
    """
    Menghitung skor kecocokan antara teks CV dan deskripsi pekerjaan.
    
    Args:
        cv_text (str): Teks dari konten CV.
        job_desc_text (str): Teks dari deskripsi pekerjaan.
        
    Returns:
        float: Skor kecocokan dalam persentase (0-100).
        
    Raises:
        ValueError: Jika input teks kosong atau tidak valid.
    """
    # Validasi input
    if not isinstance(cv_text, str) or not isinstance(job_desc_text, str):
        raise ValueError("Input harus berupa string")
        
    if not cv_text.strip() or not job_desc_text.strip():
        return 0.0

    try:
        # Preprocessing dokumen
        documents: List[str] = [cv_text, job_desc_text]
        tfidf: TfidfVectorizer = TfidfVectorizer(stop_words='english')
        
        # Transform dokumen ke matrix TF-IDF
        tfidf_matrix = tfidf.fit_transform(documents)
        
        # Hitung cosine similarity
        cosine_sim: np.ndarray = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
        
        # Konversi ke persentase dan bulatkan
        match_score: float = float(cosine_sim[0][0]) * 100
        return round(match_score, 2)
        
    except Exception as e:
        print(f"Error dalam perhitungan skor: {str(e)}")
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

if __name__ == '__main__':
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
    
    Education:
    - S1 Teknik Informatika, Universitas Gadjah Mada
    """

    sample_job_description = """
    We are hiring a Python Developer.
    Must have experience with Flask framework and REST API development.
    Knowledge of SQL is required. ReactJS is a plus. Docker is nice to have.
    """

    print("--- 1. Menguji Fungsi Parsing Info Kandidat ---")
    pprint.pprint(parse_candidate_info(sample_cv_text))
    print("\n" + "="*40 + "\n")

    print("--- 2. Menguji Fungsi Scoring Kecocokan ---")
    score = calculate_match_score(sample_cv_text, sample_job_description)
    print(f"SKOR KECOCOKAN: {score}%")
    print("\n" + "="*40 + "\n")

    print("--- 3. Menguji Fungsi ATS Check ---")
    pprint.pprint(check_ats_friendliness(sample_cv_text))
    print("\n" + "="*40 + "\n")

    print("--- 4. Menguji Fungsi Analisis Keyword ---")
    pprint.pprint(analyze_keywords(sample_cv_text, sample_job_description))
    print("\n" + "="*40 + "\n")