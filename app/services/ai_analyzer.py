import spacy
import re
import pprint
import datetime
import warnings
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Pustaka tambahan untuk model NER Bahasa Indonesia
try:
    from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
    import torch
    # Menonaktifkan peringatan spesifik dari Hugging Face saat loading model
    warnings.filterwarnings("ignore", "Some weights of the model were not initialized")
except ImportError:
    print("ERROR: Pustaka 'transformers' atau 'torch' tidak ditemukan. Harap install dengan 'pip install transformers torch'")

# --- 1. INISIALISASI MODEL ---

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
        aggregation_strategy="simple" # Menggabungkan sub-kata menjadi satu entitas
    )
    print(f"--- Model NER Indonesia '{model_name}' (Hugging Face) berhasil dimuat. ---")
except Exception as e:
    print(f"ERROR: Gagal memuat model NER Indonesia: {e}")

# Daftar kata kunci skill untuk dicari
SKILL_KEYWORDS = [
    'python', 'java', 'c++', 'javascript', 'react', 'reactjs', 'node.js', 'nodejs',
    'flask', 'django', 'spring boot', 'html', 'css', 'tailwind',
    'sql', 'mysql', 'postgresql', 'mongodb', 'database',
    'docker', 'git', 'aws', 'api', 'rest api', 'machine learning',
    'data analysis', 'data science', 'business intelligence', 'seo',
    'digital marketing', 'content marketing', 'sem', 'google analytics'
]


# --- 2. FUNGSI-FUNGSI HELPER UNTUK AI ---
def normalize_name(name: str) -> str:
    """Normalisasi nama: kapitalisasi tiap kata, kecuali singkatan full uppercase."""
    if not name:
        return None
    words = name.split()
    normalized_words = []
    for w in words:
        # kalau kata uppercase penuh (misalnya BEM, PT) biarkan
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

def parse_candidate_info(text):
    """
    Mengekstrak informasi terstruktur:
    - Nama: Menggunakan BERT NER Indonesia.
    - Lainnya: Menggunakan Regex dan Keyword Matching.
    """
    if NER_INDONESIA_PIPELINE is None:
        print("ERROR: Model NER Indonesia tidak dimuat, parsing dibatalkan.")
        return {}
    
    # 1. Inisialisasi dictionary
    extracted_data = { 
        "name": None, "email": None, "phone": None, "gpa": None, 
        'experience': 0, "skills": [] 
    }

    # 2. Ekstrak NAMA menggunakan NER Indonesia
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

    # 2. Fallback regex (ambil first line kalau masuk akal)
    if not best_name:
        lines = text.strip().splitlines()
        if lines:
            first_line = lines[0].strip()
            if not re.search(r'@|\d|https?://', first_line):
                best_name = first_line
            elif first_line.isupper() and len(first_line.split()) >= 2:
                best_name = first_line

    # 3. Fallback tambahan (cari baris sebelum email/phone)
    if not best_name:
        best_name = extract_name_with_fallback(text)

    # 4. Normalisasi akhir
    extracted_data['name'] = normalize_name(best_name)


                
    # 3. Ekstrak informasi lainnya dari teks mentah
    text_lower = text.lower()
    
    # Ekstraksi Email (menggunakan regex yang sama)
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    if email_match: extracted_data['email'] = email_match.group(0)

    # Ekstraksi Nomor Telepon (menggunakan regex yang sama)
    phone_match = re.search(r'(\+62|0)8[1-9][0-9]{7,10}\b', text)
    if phone_match: extracted_data['phone'] = phone_match.group(0)
        
    # Ekstraksi Skills (menggunakan logika keyword matching yang sama)
    found_skills = set()
    for keyword in SKILL_KEYWORDS:
        if keyword in text_lower: found_skills.add(keyword.title())
    extracted_data['skills'] = list(found_skills)
    
    # 4. Ekstraksi IPK (GPA) (menggunakan logika regex yang sama)
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
        
    # Ekstraksi dan Perhitungan Tahun Pengalaman (menggunakan logika regex yang sama)
    year_ranges = re.findall(r'(\d{4})\s*-\s*(\d{4}|present|sekarang)', text, re.IGNORECASE)
    total_years = 0
    current_year = datetime.datetime.now().year
    
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
    
# --- 3. BLOK UNTUK TESTING ---
if __name__ == '__main__':
    # Teks CV yang sama untuk diuji
    sample_cv_text = """
    Member of IT Division, Battle of Minds 2023​
(May, 2023) - (June, 2023)
Tech Stack: HTML, CSS, JavaScript, Bootstrap

Shella Valensia Sitanaya
shellasitanaya@gmail.com | https://www.linkedin.com/in/shellavalensiasitanaya | 081385613902 |

●​
Battle of Minds (BOM) is a logic and mathematics competition for high school students, aiming to challenge
and enhance their analytical thinking skills
●​
Developed registration forms and competition phase tracking section to manage participant progress
throughout the event
Member of IT Division, TKMDII 2025​
(May, 2025) - (August, 2025)
Tech Stack: HTML, CSS, Laravel

github.com/shellasitanaya


I am a detail-oriented Business Information Systems student with strong skills in Python, SQL, and Excel, while
actively developing my skills in Power BI for dashboards and business reporting. Through projects and competitions, I        
have gained experience in predictive analytics, logistics optimization, and statistical analysis. With both technical        
expertise and organizational leadership experience, I am eager to contribute to data-driven decision-making at Samator       
Group while continuously expanding my expertise in analytics and business intelligence.

EDUCATION​



Business Information System Student - (Petra Christian University)​
(2023) - (Now)
●​
Current GPA: 3,94/4.00
●​
Relevant coursework: Business Intelligence, Design Analysis of Information Systems, Artificial Intelligence &
Machine Learning, Business Process Analysis, Multi Criteria Decision Making, Statistics.
High School Diploma – (High School 1 Ambon)​
(2020) – (2023)
●​
Majoring in Natural Sciences.

PROJECTS


Predictive Maintenance for Paving Machines - FACT Program - Access repository here​
(Jan, 2025)
Tech stack: Pandas, Matplotlib, NumPy, Streamlit, Seaborn
    """
    
    print("\n--- Menguji Fungsi Parsing Info dengan Model NER Indonesia (BERT) ---")
    parsed_info = parse_candidate_info(sample_cv_text)
    
    print("\nHasil Parsing:")
    pprint.pprint(parsed_info)