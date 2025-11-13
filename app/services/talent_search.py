# filename: backend-cv-analyzer/app/services/talent_search.py
from app.models import Candidate
from sqlalchemy import or_, func
from app.extensions import db

# ✅ MODIFIKASI: Kamus pemetaan Role ke Skills
# Kuncinya (key) sekarang adalah TUPLE yang berisi semua alias/singkatan.
# Kita akan menggunakan huruf kecil semua untuk pencocokan.
ROLE_SKILL_MAP = {
    ("web development", "web dev", "frontend", "web developer"): [
        "html", "css", "javascript", "react", "angular", "vue", 
        "node.js", "php", "laravel", "django", "ruby on rails", "frontend"
    ],
    ("software engineer", "soft eng", "swe", "backend", "software developer"): [
        "python", "java", "c++", "c#", "golang", "backend", "api",
        "docker", "kubernetes", "aws", "gcp", "azure", "microservices"
    ],
    ("business analyst", "ba", "bi analyst"): [
        "sql", "excel", "power bi", "tableau", "statistics", "data analysis", "metabase"
    ],
    ("data scientist", "data science", "ds"): [
        "python", "r", "sql", "tensorflow", "pytorch", "scikit-learn", 
        "pandas", "numpy", "machine learning", "deep learning"
    ],
    ("mobile developer", "mobile dev", "android dev", "ios dev"): [
        "kotlin", "swift", "react native", "flutter", "android", "ios"
    ]
}


def search_candidates(keyword: str):
    """
    Cari kandidat berdasarkan nama, email, telepon, atau skill.
    Sekarang juga mendukung pencarian berdasarkan role DAN ALIAS-nya (misal "web dev").
    """

    keyword_lower = keyword.lower()

    # ✅ MODIFIKASI: Logika baru untuk menemukan skill berdasarkan alias
    search_terms = []
    found_role = False

    # 1. Iterasi melalui map (yang kuncinya adalah tuple)
    for aliases_tuple, skills_list in ROLE_SKILL_MAP.items():
        if keyword_lower in aliases_tuple:
            search_terms = skills_list  # Gunakan daftar skill yang sesuai
            found_role = True
            break  # Ditemukan, hentikan iterasi

    # 2. Jika tidak ditemukan di role manapun, gunakan keyword asli
    if not found_role:
        search_terms = [keyword_lower]

    # --- Dari sini ke bawah, logikanya sama persis seperti sebelumnya ---

    # 3. Buat daftar kondisi 'OR' secara dinamis
    or_conditions = []

    for term in search_terms:
        # Buat pola LIKE untuk setiap term (skill atau keyword asli)
        like_pattern = f"%{term}%"

        # Tambahkan kondisi pencarian untuk setiap term
        or_conditions.append(func.lower(Candidate.extracted_name).like(like_pattern))
        or_conditions.append(func.lower(Candidate.extracted_email).like(like_pattern))
        or_conditions.append(func.lower(Candidate.extracted_phone).like(like_pattern))
        
        # Mencari di dalam array JSON 'hard_skills'
        or_conditions.append(
            func.lower(
                func.json_extract(Candidate.structured_profile_json, '$.hard_skills')
            ).like(like_pattern)
        )

    if not or_conditions:
        return []

    # 4. Eksekusi query dengan semua kondisi OR
    query = Candidate.query.filter(or_(*or_conditions)).distinct().all()

    # 5. Ubah ke bentuk JSON-friendly
    results = []
    for c in query:
        results.append({
            "id": c.id,
            "name": c.extracted_name,
            "email": c.extracted_email,
            "phone": c.extracted_phone,
            "match_score": float(c.match_score) if c.match_score else None,
            "status": c.status,
            "hard_skills": c.structured_profile_json.get("hard_skills", []) if c.structured_profile_json else [],
            # "job_title": c.structured_profile_json.get("job_title", "N/A"),
            # "university": c.structured_profile_json.get("university", "N/A"),
            # "location": c.structured_profile_json.get("location", "N/A"),
            # "current_company": c.structured_profile_json.get("current_company", "N/A"),
            # "gpa": c.structured_profile_json.get("gpa", "N/A"),
            # "experience": c.structured_profile_json.get("total_experience", "N/A"),
        })

    return results