from app.models import Candidate, Skill, CandidateSkill
from sqlalchemy import or_, func, and_
from app.extensions import db
import re

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
        
        input_words = input_lower.split()
        role_words = role.split()
        
        exact_matches = len(set(input_words) & set(role_words))
        if exact_matches > 0:
            score = 0.6 + (exact_matches / max(len(input_words), len(role_words))) * 0.4
        
        if input_lower in role:
            substring_score = 0.7 + (len(input_lower) / len(role)) * 0.3
            score = max(score, substring_score)
        
        if role in input_lower and len(role) >= 3:
            contains_score = 0.8 + (len(role) / len(input_lower)) * 0.2
            score = max(score, contains_score)
        
        partial_matches = 0
        for i_word in input_words:
            for r_word in role_words:
                if (i_word.startswith(r_word) or 
                    r_word.startswith(i_word) or 
                    (len(i_word) >= 3 and r_word in i_word) or 
                    (len(r_word) >= 3 and i_word in r_word)):
                    partial_matches += 1
                    break
        
        partial_score = (partial_matches / max(len(input_words), len(role_words))) * 0.8
        score = max(score, partial_score)
        
        if score > best_score and score > 0.6:
            best_score = score
            best_match = role

    print(f"🔍 Fuzzy match backend: '{input_text}' → '{best_match}' (score: {best_score})")
    return best_match

def search_candidates(keyword: str):
    """
    Cari kandidat berdasarkan kombinasi role dan skill dengan scoring yang lebih baik
    """
    keyword_lower = keyword.lower().strip()
    
    if not keyword_lower:
        return []
    
    print(f"🎯 Starting search for: '{keyword}'")
    
    # ============================
    # 1. Identifikasi Role dan Skill
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
    
    # ============================
    # 2. Eksekusi Query dengan Prioritas Skill Match
    # ============================
    try:
        # Untuk kombinasi role + skill, kita akan lakukan query terpisah
        # untuk memastikan kandidat dengan skill match lebih tinggi diutamakan
        
        if role_terms and skill_terms:
            # CASE 1: Kombinasi Role + Skill - UTAMAKAN SKILL MATCH
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
                .order_by(func.count(Skill.id).desc())  # Urutkan berdasarkan jumlah skill match
                .all()
            )
            
            results = []
            for candidate, matched_count in query:
                try:
                    # Ambil semua skill kandidat
                    db_skills = []
                    if hasattr(candidate, 'candidate_skills'):
                        db_skills = [cs.skill.skill_name for cs in candidate.candidate_skills if cs.skill]
                    
                    # Hitung match score dengan bobot skill yang lebih tinggi
                    total_searched = len(skill_terms)
                    skill_match_ratio = matched_count / total_searched if total_searched > 0 else 0
                    
                    # Beri bobot lebih tinggi untuk skill match (80%) vs role match (20%)
                    role_match_score = 20 if role_terms else 0
                    skill_match_score = skill_match_ratio * 80
                    overall_match_score = min(100, role_match_score + skill_match_score)
                    
                    candidate_data = {
                        "id": candidate.id,
                        "name": candidate.name,
                        "email": candidate.email,
                        "phone": candidate.phone,
                        "match_score": float(overall_match_score),
                        "matched_skills_count": matched_count,
                        "total_searched_skills": total_searched,
                        "has_role_match": bool(role_terms),
                        "role_matched": closest_role,
                        "status": candidate.status,
                        "skills": db_skills,
                        "experience": getattr(candidate, 'experience', ''),
                        "university": getattr(candidate, 'education', ''),
                    }
                    
                    candidate_data = {k: v for k, v in candidate_data.items() if v is not None}
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
                    "university": getattr(candidate, 'education', ''),
                }
                
                candidate_data = {k: v for k, v in candidate_data.items() if v is not None}
                results.append(candidate_data)
            
            print(f"📊 Role search berhasil, ditemukan {len(results)} kandidat")
            
        elif skill_terms:
            # CASE 3: Hanya Skill search
            print("🎯 Performing SKILL-only search")
            
            skill_conditions = []
            for term in skill_terms:
                like_pattern = f"%{term}%"
                skill_conditions.append(func.lower(Skill.skill_name).like(like_pattern))
            
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
                    db_skills = []
                    if hasattr(candidate, 'candidate_skills'):
                        db_skills = [cs.skill.skill_name for cs in candidate.candidate_skills if cs.skill]
                    
                    total_searched = len(skill_terms)
                    match_percentage = min(100, int((matched_count / total_searched) * 100))
                    
                    candidate_data = {
                        "id": candidate.id,
                        "name": candidate.name,
                        "email": candidate.email,
                        "phone": candidate.phone,
                        "match_score": float(match_percentage),
                        "matched_skills_count": matched_count,
                        "total_searched_skills": total_searched,
                        "has_role_match": False,
                        "role_matched": None,
                        "status": candidate.status,
                        "skills": db_skills,
                        "experience": getattr(candidate, 'experience', ''),
                        "university": getattr(candidate, 'education', ''),
                    }
                    
                    candidate_data = {k: v for k, v in candidate_data.items() if v is not None}
                    results.append(candidate_data)
                    
                except Exception as e:
                    print(f"❌ Error memproses kandidat {candidate.id}: {e}")
                    continue
            
            print(f"📊 Skill search berhasil, ditemukan {len(results)} kandidat")
        
        else:
            return []
        
        # Debug info
        if results:
            print(f"🎉 Berhasil memproses {len(results)} kandidat")
            for result in results[:3]:
                if result['has_role_match'] and result['total_searched_skills'] > 0:
                    print(f"   - {result['name']}: Role '{result['role_matched']}' + {result['matched_skills_count']}/{result['total_searched_skills']} skills - Score: {result['match_score']}%")
                elif result['has_role_match']:
                    print(f"   - {result['name']}: Role '{result['role_matched']}' - Score: {result['match_score']}%")
                else:
                    print(f"   - {result['name']}: {result['matched_skills_count']}/{result['total_searched_skills']} skills - Score: {result['match_score']}%")
        else:
            print("❌ Tidak ada hasil yang ditemukan")
        
        return results
        
    except Exception as e:
        print(f"❌ Error dalam query: {e}")
        return []