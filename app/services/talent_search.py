from app.models import Candidate, Skill, CandidateSkill
from sqlalchemy import or_, func, and_
from app.extensions import db
import re
from difflib import SequenceMatcher

# ============================
# Role/Job Title Mapping untuk Experience Search
# ============================
ROLE_JOB_MAP = {
    # ===== SOFTWARE ENGINEERING & IT =====
    "software engineer": [
        "software engineer", "software developer", "swe", "backend developer",
        "frontend developer", "fullstack developer", "full stack developer",
        "mobile developer", "android developer", "ios developer",
        "devops engineer", "cloud engineer", "site reliability engineer",
        "sre", "machine learning engineer", "ai engineer",
        "data engineer", "data scientist", "ml engineer"
    ],
    "software developer": ["software developer", "software engineer", "backend developer"],
    "swe": ["software engineer", "software developer"],
    "backend": ["backend developer", "backend engineer", "software engineer"],
    "frontend": ["frontend developer", "web developer", "react developer", "vue developer"],
    "fullstack": ["fullstack developer", "full stack developer", "software engineer"],
    "web developer": ["web developer", "frontend developer", "web development"],
    "ios dev": ["ios developer", "mobile developer", "swift developer"],
    "android dev": ["android developer", "mobile developer", "kotlin developer"],
    "mobile dev": ["mobile developer", "android developer", "ios developer"],

    # ===== DATA JOBS =====
    "data scientist": [
        "data scientist", "machine learning engineer", "ai engineer",
        "data analyst", "ml engineer", "ai researcher"
    ],
    "data science": ["data scientist", "data science", "machine learning"],
    "data analyst": ["data analyst", "business intelligence analyst", "bi analyst"],
    "business analyst": ["business analyst", "data analyst", "product analyst"],
    "bi analyst": ["bi analyst", "business intelligence analyst", "data analyst"],
    "data engineer": ["data engineer", "etl engineer", "big data engineer"],

    # ===== PRODUCT =====
    "product manager": [
        "product manager", "product owner", "pm", "product strategist",
        "product lead"
    ],
    "product owner": ["product owner", "product manager"],
    "scrum master": ["scrum master", "agile coach"],

    # ===== DESIGN & CREATIVE =====
    "ui ux": ["ui designer", "ux designer", "ui/ux designer", "product designer"],
    "designer": ["graphic designer", "ui designer", "visual designer", "ui designer", "ux designer", "ui/ux designer"],
    "graphic designer": ["graphic designer", "visual designer"],
    "motion designer": ["motion designer", "motion graphic artist"],
    "video editor": ["video editor", "videographer"],

    # ===== MARKETING =====
    "digital marketing": [
        "digital marketing", "performance marketing", "seo specialist",
        "content marketing", "social media specialist", "ads specialist"
    ],
    "seo": ["seo specialist", "seo analyst"],
    "social media": ["social media specialist", "content creator"],
    "content creator": ["content creator", "content specialist"],

    # ===== SALES & BUSINESS =====
    "sales": ["sales executive", "sales consultant", "account executive", "sales representative"],
    "account executive": ["account executive", "sales executive"],
    "business development": ["business development", "bd", "partnership manager"],
    "real estate": ["real estate agent", "property consultant"],

    # ===== MANAGEMENT & OPERATIONS =====
    "project manager": ["project manager", "project coordinator", "program manager"],
    "project coordinator": ["project coordinator", "project assistant"],
    "operations": ["operations staff", "operations manager", "ops analyst"],
    "logistics": ["logistics staff", "warehouse staff", "supply chain"],

    # ===== HR =====
    "hr": ["human resources", "hr staff", "hr generalist", "hr officer"],
    "recruiter": ["recruiter", "talent acquisition"],
    "talent acquisition": ["talent acquisition", "recruiter"],

    # ===== FINANCE =====
    "accounting": ["accounting", "accountant", "finance staff"],
    "finance": ["finance staff", "financial analyst"],
    "tax": ["tax officer", "tax consultant"],

    # ===== ENGINEERING (NON IT) =====
    "mechanical engineer": ["mechanical engineer", "mechatronics engineer"],
    "electrical engineer": ["electrical engineer", "electronics engineer"],
    "civil engineer": ["civil engineer", "site engineer"],
    "mechatronics": ["mechatronics engineer", "robotics engineer"],
    "robotics": ["robotics engineer", "automation engineer"],

    # ===== MANUFACTURING =====
    "operator": ["operator", "production operator", "machine operator"],
    "quality control": ["quality control", "qc staff", "quality assurance"],

    # ===== ADMIN =====
    "admin": ["administration", "admin staff", "office admin"],
    "customer service": ["customer service", "cs staff"],

    # ===== MEDICAL =====
    "nurse": ["nurse", "perawat"],
    "doctor": ["doctor", "dokter"],
    "pharmacist": ["pharmacist", "apoteker"],

    # ===== EDUCATION =====
    "teacher": ["teacher", "guru", "instructor"],
    "tutor": ["tutor", "private tutor"],

    # ===== SECURITY =====
    "security": ["security", "satpam"],

    # ===== HOSPITALITY =====
    "chef": ["chef", "cook"],
    "waiter": ["waiter", "waitress", "server"],
}

# Fungsi fuzzy matching untuk role
def find_closest_role(input_text):
    input_lower = input_text.lower().strip()
    
    if not input_lower:
        return None

    if input_lower in ROLE_JOB_MAP:
        return input_lower

    best_match = None
    best_score = 0

    for role in ROLE_JOB_MAP.keys():
        if len(input_lower) < 3:
            continue

        score = 0
        
        # Check for similarity using SequenceMatcher
        similarity = SequenceMatcher(None, input_lower, role).ratio()
        if similarity > 0.7:
            score = similarity
        
        if score > best_score:
            best_score = score
            best_match = role

    return best_match

# Fungsi untuk mendeteksi apakah input adalah nama (berdasarkan pola)
def is_likely_name(input_text):
    """
    Deteksi apakah input kemungkinan adalah nama seseorang
    - Tidak mengandung kata kunci role yang umum
    - Biasanya 2-3 kata
    - Boleh huruf kapital atau tidak
    """
    if not input_text:
        return False
    
    input_lower = input_text.lower().strip()
    words = input_lower.split()
    
    # Jika hanya 1 kata, mungkin nama panggilan
    if len(words) < 1 or len(words) > 4:
        return False
    
    # Cek jika mengandung angka - pasti bukan nama
    if any(char.isdigit() for char in input_text):
        return False
    
    # Cek jika mengandung karakter khusus yang bukan nama
    special_chars = ['@', '#', '$', '%', '&', '*', '+', '=', '<', '>', '/', '\\']
    if any(char in input_text for char in special_chars):
        return False
    
    # Kata kunci role yang umum - jika ada, bukan nama
    common_role_keywords = [
        'developer', 'engineer', 'designer', 'analyst', 'manager', 
        'specialist', 'intern', 'junior', 'senior', 'lead', 'frontend',
        'backend', 'fullstack', 'mobile', 'web', 'software', 'data',
        'ui', 'ux', 'devops', 'cloud', 'machine', 'learning', 'ai',
        'database', 'administrator', 'support', 'technical', 'customer',
        'service', 'sales', 'marketing', 'content', 'seo', 'social',
        'media', 'product', 'project', 'scrum', 'agile', 'quality',
        'control', 'assurance', 'operations', 'hr', 'human', 'resources',
        'recruiter', 'talent', 'finance', 'accounting', 'tax', 'medical',
        'nurse', 'doctor', 'pharmacist', 'teacher', 'tutor', 'security',
        'chef', 'waiter', 'mechanic', 'electrical', 'civil', 'robotics',
        'automation', 'production', 'machine', 'admin', 'administration',
        'logistics', 'supply', 'chain', 'warehouse', 'driver'
    ]
    
    # Cek setiap kata apakah termasuk keyword role
    for word in words:
        if word in common_role_keywords:
            print(f"❌ Rejected as name: contains role keyword '{word}'")
            return False
    
    # Cek jika terlalu panjang untuk nama (lebih dari 30 karakter tanpa spasi)
    if len(input_text.replace(' ', '')) > 30:
        return False
    
    # Cek pola umum nama:
    # - Biasanya mengandung huruf dan spasi saja
    # - Tidak ada kata yang terlalu panjang (lebih dari 10 huruf)
    for word in words:
        if len(word) > 15:  # Kata terlalu panjang untuk nama
            return False
    
    # Jika lolos semua pengecekan, kemungkinan besar adalah nama
    print(f"✅ Detected as likely name: {input_text}")
    return True

# Fungsi untuk search nama
def search_by_name(name_query):
    """Search candidates by name with fuzzy matching"""
    name_lower = name_query.lower().strip()
    
    if not name_lower:
        return []
    
    try:
        # Split nama menjadi kata-kata
        name_words = name_lower.split()
        
        # Build conditions untuk setiap kata dalam nama
        name_conditions = []
        for word in name_words:
            if len(word) >= 2:  # Minimal 2 karakter
                name_conditions.append(func.lower(Candidate.name).like(f"%{word}%"))
        
        if not name_conditions:
            return []
        
        query = (
            db.session.query(Candidate)
            .filter(or_(*name_conditions))
            .all()
        )
        
        results = []
        for candidate in query:
            # Get candidate skills
            db_skills = []
            if hasattr(candidate, 'candidate_skills'):
                db_skills = [cs.skill.skill_name for cs in candidate.candidate_skills if cs.skill]
            
            # Calculate match score for name
            candidate_name_lower = candidate.name.lower()
            similarity = SequenceMatcher(None, name_lower, candidate_name_lower).ratio()
            name_match_score = int(similarity * 100)
            
            candidate_data = {
                "id": candidate.id,
                "name": candidate.name,
                "email": candidate.email,
                "phone": candidate.phone,
                "match_score": name_match_score,
                "matched_skills_count": 0,
                "total_searched_skills": 0,
                "has_role_match": False,
                "role_matched": None,
                "status": candidate.status,
                "skills": db_skills,
                "experience": getattr(candidate, 'experience', ''),
                "education": getattr(candidate, 'education', ''),
                "search_type": "name"
            }
            
            results.append(candidate_data)
        
        # Sort by name match score
        results.sort(key=lambda x: x['match_score'], reverse=True)
        
        print(f"🔍 Name search for '{name_query}' found {len(results)} candidates")
        return results
        
    except Exception as e:
        print(f"❌ Error in name search: {e}")
        return []

# Fungsi untuk search skill saja (tanpa role)
def search_by_skills_only(skill_terms):
    """Search candidates based only on skills"""
    if not skill_terms:
        return []
    
    try:
        print(f"🎯 Performing SKILLS-ONLY search for: {skill_terms}")
        
        # Build skill conditions
        skill_conditions = []
        for term in skill_terms:
            like_pattern = f"%{term}%"
            skill_conditions.append(func.lower(Skill.skill_name).like(like_pattern))
        
        # Query untuk skill match dengan counting
        query = (
            db.session.query(
                Candidate,
                func.count(Skill.id).label('matched_skills_count')
            )
            .join(CandidateSkill, Candidate.id == CandidateSkill.candidate_id)
            .join(Skill, Skill.id == CandidateSkill.skill_id)
            .filter(or_(*skill_conditions))
            .group_by(Candidate.id)
            .order_by(func.count(Skill.id).desc())
            .all()
        )
        
        results = []
        for candidate, matched_count in query:
            try:
                # Get all candidate skills
                db_skills = []
                if hasattr(candidate, 'candidate_skills'):
                    db_skills = [cs.skill.skill_name for cs in candidate.candidate_skills if cs.skill]
                
                total_searched = len(skill_terms)
                skill_match_ratio = matched_count / total_searched if total_searched > 0 else 0
                match_score = int(skill_match_ratio * 100)
                
                candidate_data = {
                    "id": candidate.id,
                    "name": candidate.name,
                    "email": candidate.email,
                    "phone": candidate.phone,
                    "match_score": match_score,
                    "matched_skills_count": matched_count,
                    "total_searched_skills": total_searched,
                    "has_role_match": False,
                    "role_matched": None,
                    "status": candidate.status,
                    "skills": db_skills,
                    "experience": getattr(candidate, 'experience', ''),
                    "education": getattr(candidate, 'education', ''),
                    "search_type": "skills_only"
                }
                
                results.append(candidate_data)
                
            except Exception as e:
                print(f"❌ Error processing candidate {candidate.id}: {e}")
                continue
        
        print(f"📊 Skill-only search berhasil, ditemukan {len(results)} kandidat")
        return results
        
    except Exception as e:
        print(f"❌ Error in skill-only search: {e}")
        return []

# Fungsi untuk search all candidates (no filter)
def get_all_candidates():
    """Get all candidates without any filtering"""
    try:
        candidates = Candidate.query.all()
        
        results = []
        for candidate in candidates:
            # Get candidate skills
            db_skills = []
            if hasattr(candidate, 'candidate_skills'):
                db_skills = [cs.skill.skill_name for cs in candidate.candidate_skills if cs.skill]
            
            candidate_data = {
                "id": candidate.id,
                "name": candidate.name,
                "email": candidate.email,
                "phone": candidate.phone,
                "match_score": float(candidate.match_score) if candidate.match_score else 50.0,
                "matched_skills_count": 0,
                "total_searched_skills": 0,
                "has_role_match": False,
                "role_matched": None,
                "status": candidate.status,
                "skills": db_skills,
                "experience": getattr(candidate, 'experience', ''),
                "education": getattr(candidate, 'education', ''),
                "search_type": "all"
            }
            
            results.append(candidate_data)
        
        print(f"📊 Retrieved all {len(results)} candidates")
        return results
        
    except Exception as e:
        print(f"❌ Error getting all candidates: {e}")
        return []

def search_candidates(keyword: str):
    """
    Cari kandidat berdasarkan kombinasi role, skill, atau name
    """
    keyword_lower = keyword.lower().strip()
    
    # Jika keyword kosong atau "all", return semua kandidat
    if not keyword_lower or keyword_lower == "all" or keyword_lower == "semua":
        print(f"🔍 Returning ALL candidates for keyword: '{keyword}'")
        return get_all_candidates()
    
    print(f"🎯 Starting search for: '{keyword}'")
    
    # ============================
    # 1. Cek apakah ini name search
    # ============================
    if is_likely_name(keyword):
        print(f"👤 Detected as NAME search: {keyword}")
        return search_by_name(keyword)
    
    # ============================
    # 2. Identifikasi Role dan Skill
    # ============================
    role_terms = []
    skill_terms = []
    
    # Cari role menggunakan fuzzy matching
    closest_role = find_closest_role(keyword_lower)
    if closest_role:
        role_terms = ROLE_JOB_MAP[closest_role]
        print(f"✅ Role detected: {closest_role} → {role_terms}")
        
        # Untuk skill terms, ambil kata-kata yang tidak termasuk dalam role
        remaining_terms = []
        role_words = set(closest_role.split())
        for word in keyword_lower.split():
            word_clean = word.strip()
            if (word_clean and len(word_clean) >= 2 and 
                not any(role_word in word_clean or word_clean in role_word 
                       for role_word in role_words)):
                remaining_terms.append(word_clean)
        
        if remaining_terms:
            skill_terms = remaining_terms
            print(f"🔍 Skill terms from remaining: {skill_terms}")
    else:
        # Jika tidak ada role yang terdeteksi, anggap semua sebagai skill
        skill_terms = [term.strip() for term in re.split(r'[,\s]+', keyword_lower) if term.strip()]
        print(f"🔍 Pure skill search: {skill_terms}")
        
        # Jika hanya skill terms tanpa role, lakukan skill-only search
        if skill_terms and not role_terms:
            return search_by_skills_only(skill_terms)
    
    # ============================
    # 3. Eksekusi Query berdasarkan kondisi
    # ============================
    try:
        if role_terms and skill_terms:
            # CASE 1: Kombinasi Role + Skill
            print("🎯 Performing ROLE + SKILL search with skill priority")
            
            # Buat kondisi untuk role
            role_conditions = []
            for term in role_terms:
                role_conditions.append(func.lower(Candidate.experience).like(f"%{term}%"))
            
            # Buat kondisi untuk skill
            skill_conditions = []
            for term in skill_terms:
                like_pattern = f"%{term}%"
                skill_conditions.append(func.lower(Skill.skill_name).like(like_pattern))
            
            # Query untuk kandidat yang match role DAN skill
            query = (
                db.session.query(
                    Candidate,
                    func.count(Skill.id).label('matched_skills_count')
                )
                .join(CandidateSkill, Candidate.id == CandidateSkill.candidate_id)
                .join(Skill, Skill.id == CandidateSkill.skill_id)
                .filter(and_(
                    or_(*role_conditions),
                    or_(*skill_conditions)
                ))
                .group_by(Candidate.id)
                .order_by(func.count(Skill.id).desc())
                .all()
            )
            
            results = []
            for candidate, matched_count in query:
                try:
                    # Ambil semua skill kandidat
                    db_skills = []
                    if hasattr(candidate, 'candidate_skills'):
                        db_skills = [cs.skill.skill_name for cs in candidate.candidate_skills if cs.skill]
                    
                    # Hitung match score
                    total_searched = len(skill_terms)
                    skill_match_ratio = matched_count / total_searched if total_searched > 0 else 0
                    
                    # Weighted score: role match (40%) + skill match (60%)
                    role_match_score = 40  # Karena role match ditemukan
                    skill_match_score = skill_match_ratio * 60
                    overall_match_score = min(100, role_match_score + skill_match_score)
                    
                    candidate_data = {
                        "id": candidate.id,
                        "name": candidate.name,
                        "email": candidate.email,
                        "phone": candidate.phone,
                        "match_score": float(overall_match_score),
                        "matched_skills_count": matched_count,
                        "total_searched_skills": total_searched,
                        "has_role_match": True,
                        "role_matched": closest_role,
                        "status": candidate.status,
                        "skills": db_skills,
                        "experience": getattr(candidate, 'experience', ''),
                        "education": getattr(candidate, 'education', ''),
                        "search_type": "role_skills"
                    }
                    
                    results.append(candidate_data)
                    
                except Exception as e:
                    print(f"❌ Error memproses kandidat {candidate.id}: {e}")
                    continue
            
            print(f"📊 Role+Skill search berhasil, ditemukan {len(results)} kandidat")
            
        elif role_terms:
            # CASE 2: Hanya Role search
            print("🎯 Performing ROLE-only search")
            
            role_conditions = []
            for term in role_terms:
                role_conditions.append(func.lower(Candidate.experience).like(f"%{term}%"))
            
            query = (
                db.session.query(Candidate)
                .filter(or_(*role_conditions))
                .all()
            )
            
            results = []
            for candidate in query:
                db_skills = []
                if hasattr(candidate, 'candidate_skills'):
                    db_skills = [cs.skill.skill_name for cs in candidate.candidate_skills if cs.skill]
                
                candidate_data = {
                    "id": candidate.id,
                    "name": candidate.name,
                    "email": candidate.email,
                    "phone": candidate.phone,
                    "match_score": float(candidate.match_score) if candidate.match_score else 85.0,
                    "matched_skills_count": 1,
                    "total_searched_skills": 1,
                    "has_role_match": True,
                    "role_matched": closest_role,
                    "status": candidate.status,
                    "skills": db_skills,
                    "experience": getattr(candidate, 'experience', ''),
                    "education": getattr(candidate, 'education', ''),
                    "search_type": "role_only"
                }
                
                results.append(candidate_data)
            
            print(f"📊 Role search berhasil, ditemukan {len(results)} kandidat")
            
        elif skill_terms:
            # CASE 3: Hanya Skill search
            print("🎯 Performing SKILL-only search")
            return search_by_skills_only(skill_terms)
        
        else:
            # CASE 4: Tidak ada kriteria, kembalikan semua
            print("📊 No criteria, returning all candidates")
            return get_all_candidates()
        
        # Debug info
        if results:
            print(f"🎉 Berhasil memproses {len(results)} kandidat")
            for result in results[:3]:
                print(f"   - {result['name']}: Score: {result['match_score']}% - Type: {result.get('search_type', 'unknown')}")
        else:
            print("❌ Tidak ada hasil yang ditemukan")
        
        return results
        
    except Exception as e:
        print(f"❌ Error dalam query: {e}")
        import traceback
        traceback.print_exc()
        return []