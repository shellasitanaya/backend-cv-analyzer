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


def search_candidates(keyword: str):
    """
    Cari kandidat berdasarkan:
    - Role/Job Title: dicari di kolom experience
    - Skills: dicari di tabel skills (seperti sebelumnya)
    """
    
    # Normalize keyword - ubah ke lowercase dan strip
    keyword_lower = keyword.lower().strip()
    
    if not keyword_lower:
        return []
    
    # ============================
    # 1. Identifikasi apakah ini Role Search atau Skill Search
    # ============================
    is_role_search = False
    search_terms = []
    
    # Cek apakah keyword lengkap adalah role
    if keyword_lower in ROLE_JOB_MAP:
        print(f"✅ Role search terdeteksi: {keyword_lower}")
        is_role_search = True
        search_terms = ROLE_JOB_MAP[keyword_lower]
    else:
        # Split keyword menjadi individual terms
        terms = [term.strip() for term in re.split(r'[,\s]+', keyword_lower) if term.strip()]
        
        # Cek setiap term apakah itu role
        role_terms_found = []
        for term in terms:
            if term in ROLE_JOB_MAP:
                print(f"✅ Role terdeteksi dalam term: {term}")
                role_terms_found.extend(ROLE_JOB_MAP[term])
        
        if role_terms_found:
            is_role_search = True
            search_terms = role_terms_found
        else:
            # Jika bukan role, gunakan sebagai skill search
            print(f"🔍 Skill search: {terms}")
            search_terms = terms
    
    # ============================
    # 2. Eksekusi Query berdasarkan jenis pencarian
    # ============================
    try:
        if is_role_search:
            # PENCARIAN BERDASARKAN ROLE/JOB TITLE DI EXPERIENCE
            print(f"🎯 Melakukan role search untuk: {search_terms}")
            
            # Buat kondisi untuk mencari di experience
            experience_conditions = []
            for term in search_terms:
                experience_conditions.append(func.lower(Candidate.experience).like(f"%{term}%"))
            
            query = (
                db.session.query(Candidate)
                .filter(or_(*experience_conditions))
                .all()
            )
            
            # Format hasil untuk role search
            results = []
            for candidate in query:
                # Ambil semua skill kandidat dari database
                db_skills = []
                if hasattr(candidate, 'candidate_skills'):
                    db_skills = [cs.skill.skill_name for cs in candidate.candidate_skills if cs.skill]
                
                candidate_data = {
                    "id": candidate.id,
                    "name": candidate.name,
                    "email": candidate.email,
                    "phone": candidate.phone,
                    "match_score": float(candidate.match_score) if candidate.match_score else None,
                    "matched_skills_count": 1,  # Untuk role search, set 1 karena match experience
                    "total_searched_skills": 1,  # Untuk role search, set 1
                    "status": candidate.status,
                    "skills": db_skills,
                    "experience": getattr(candidate, 'experience', ''),
                    "university": getattr(candidate, 'education', ''),
                }
                
                # Hapus field yang None
                candidate_data = {k: v for k, v in candidate_data.items() if v is not None}
                results.append(candidate_data)
            
            print(f"📊 Role search berhasil, ditemukan {len(results)} kandidat")
            
        else:
            # PENCARIAN BERDASARKAN SKILL (seperti sebelumnya)
            print(f"🔍 Melakukan skill search untuk: {search_terms}")
            
            if not search_terms:
                return []
            
            # Buat kondisi pencarian skill
            skill_conditions = []
            for term in search_terms:
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
                .having(func.count(Skill.id) > 0)  # Minimal 1 skill cocok
                .order_by(func.count(Skill.id).desc())  # Urutkan berdasarkan jumlah skill cocok
                .all()
            )
            
            # Format hasil untuk skill search
            results = []
            for candidate, matched_count in query:
                try:
                    # Ambil semua skill kandidat dari database
                    db_skills = []
                    if hasattr(candidate, 'candidate_skills'):
                        db_skills = [cs.skill.skill_name for cs in candidate.candidate_skills if cs.skill]
                    
                    # Hitung persentase match
                    total_searched = len(search_terms)
                    match_percentage = min(100, int((matched_count / total_searched) * 100))
                    
                    candidate_data = {
                        "id": candidate.id,
                        "name": candidate.name,
                        "email": candidate.email,
                        "phone": candidate.phone,
                        "match_score": float(candidate.match_score) if candidate.match_score else None,
                        "matched_skills_count": matched_count,
                        "total_searched_skills": total_searched,
                        "status": candidate.status,
                        "skills": db_skills,
                        "experience": getattr(candidate, 'experience', ''),
                        "university": getattr(candidate, 'education', ''),
                    }
                    
                    # Hapus field yang None
                    candidate_data = {k: v for k, v in candidate_data.items() if v is not None}
                    results.append(candidate_data)
                    
                except Exception as e:
                    print(f"❌ Error memproses kandidat {candidate.id}: {e}")
                    continue
            
            print(f"📊 Skill search berhasil, ditemukan {len(results)} kandidat")
        
    except Exception as e:
        print(f"❌ Error dalam query: {e}")
        return []
    
    # Debug info
    if results:
        print(f"🎉 Berhasil memproses {len(results)} kandidat")
        for result in results[:3]:  # Print 3 hasil pertama untuk debug
            if is_role_search:
                print(f"   - {result['name']}: Role match di experience")
            else:
                print(f"   - {result['name']}: {result['matched_skills_count']}/{result['total_searched_skills']} skills match")
    else:
        print("❌ Tidak ada hasil yang ditemukan")
    
    return results