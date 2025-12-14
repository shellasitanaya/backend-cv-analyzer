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
         'mechanic', 'electrical', 'civil', 'robotics',
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

# talent_search.py - MODIFIKASI: Prioritaskan skill search

# ... (import dan kode sebelumnya tetap sama) ...

def search_candidates(keyword: str):
    """
    Cari kandidat berdasarkan kombinasi role, skill, atau name
    LOGIKA BARU: Skill Priority - Jika role tidak ditemukan, cari berdasarkan skill
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
    all_words = re.findall(r'\b\w+\b', keyword_lower)
    
    # Skill terms: semua kata yang panjang >= 2
    skill_terms = [word.strip() for word in all_words if len(word.strip()) >= 2]
    
    # Cari role dengan fuzzy matching
    closest_role = find_closest_role(keyword_lower)
    
    print(f"📋 All words from query: {all_words}")
    print(f"🔍 Skill terms to search: {skill_terms}")
    print(f"🎯 Closest role (maybe None): {closest_role}")
    
    # ============================
    # 3. LOGIKA BARU: Skill Priority
    # ============================
    try:
        # CASE A: Ada role yang terdeteksi
        if closest_role:
            role_terms = ROLE_JOB_MAP.get(closest_role, [])
            print(f"✅ Role detected: {closest_role} → {role_terms}")
            
            # Filter out role words dari skill terms
            role_words = set(closest_role.split())
            filtered_skills = [term for term in skill_terms if term not in role_words]
            
            # Cari kandidat dengan role
            role_results = search_role_only(role_terms, closest_role)
            
            if role_results:
                print(f"✅ Found {len(role_results)} candidates with role '{closest_role}'")
                
                if filtered_skills:
                    # Filter role results by skills
                    return filter_role_candidates_by_skills(role_results, filtered_skills, closest_role)
                else:
                    return role_results
            else:
                # Jika tidak ada kandidat dengan role, cari berdasarkan skills saja
                print(f"⚠️ No candidates with role '{closest_role}', IGNORING role and searching skills only: {filtered_skills}")
                if filtered_skills:
                    return search_candidates_by_skills_only_improved(filtered_skills, ignored_role=closest_role)
                else:
                    print("❌ No skills to search after ignoring role")
                    return []
        else:
            # Tidak ada role terdeteksi, langsung skill search
            print(f"🔍 No role detected, performing SKILL-ONLY search: {skill_terms}")
            if skill_terms:
                return search_candidates_by_skills_only_improved(skill_terms, ignored_role=None)
            else:
                print("📊 No criteria, returning all candidates")
                return get_all_candidates()
        
    except Exception as e:
        print(f"❌ Error dalam query: {e}")
        import traceback
        traceback.print_exc()
        return []
    
# talent_search.py - TAMBAHKAN fungsi ini

def search_candidates_by_skills_only_improved(skill_terms, ignored_role=None):
    """
    Search candidates by skills ONLY - improved version that searches in multiple fields
    """
    if not skill_terms:
        return []
    
    print(f"🔍🔍 IMPROVED SKILL-ONLY SEARCH for: {skill_terms}")
    if ignored_role:
        print(f"📝 Note: Ignoring role '{ignored_role}' because it wasn't found")
    
    try:
        # =========== STRATEGY 1: Cari di Skills Table ===========
        skill_conditions = []
        for term in skill_terms:
            like_pattern = f"%{term}%"
            skill_conditions.append(func.lower(Skill.skill_name).like(like_pattern))
        
        # Query untuk skill match
        skill_query = (
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
        
        skill_results = []
        for candidate, matched_count in skill_query:
            try:
                # Get candidate skills
                db_skills = []
                if hasattr(candidate, 'candidate_skills'):
                    db_skills = [cs.skill.skill_name for cs in candidate.candidate_skills if cs.skill]
                
                total_searched = len(skill_terms)
                skill_match_ratio = matched_count / total_searched if total_searched > 0 else 0
                match_score = int(skill_match_ratio * 100)
                
                # Cari skill yang exact match
                matched_skill_names = []
                for skill_term in skill_terms:
                    for candidate_skill in db_skills:
                        if (skill_term.lower() in candidate_skill.lower() or 
                            candidate_skill.lower() in skill_term.lower()):
                            matched_skill_names.append(skill_term)
                            break
                
                candidate_data = {
                    "id": candidate.id,
                    "name": candidate.name,
                    "email": candidate.email,
                    "phone": candidate.phone,
                    "match_score": match_score,
                    "matched_skills_count": matched_count,
                    "total_searched_skills": total_searched,
                    "matched_skills": matched_skill_names,
                    "has_role_match": False,
                    "role_matched": ignored_role if ignored_role else None,
                    "status": candidate.status,
                    "skills": db_skills,
                    "experience": getattr(candidate, 'experience', ''),
                    "education": getattr(candidate, 'education', ''),
                    "search_type": "skills_only_improved",
                    "match_note": f"Found by skills only: {', '.join(matched_skill_names[:3])}" + 
                                  (f" (ignored role: {ignored_role})" if ignored_role else "")
                }
                
                skill_results.append(candidate_data)
                
            except Exception as e:
                print(f"❌ Error processing candidate {candidate.id}: {e}")
                continue
        
        print(f"📊 Skill table search found: {len(skill_results)} candidates")
        
        # =========== STRATEGY 2: Cari di Experience field ===========
        if len(skill_results) < 5:  # Jika hasil sedikit, cari di experience
            print(f"🔍 Not enough results ({len(skill_results)}), searching in EXPERIENCE field...")
            
            experience_conditions = []
            for term in skill_terms:
                like_pattern = f"%{term}%"
                experience_conditions.append(func.lower(Candidate.experience).like(like_pattern))
            
            experience_query = (
                db.session.query(Candidate)
                .filter(or_(*experience_conditions))
                .all()
            )
            
            for candidate in experience_query:
                # Skip jika sudah ada di skill_results
                if any(r['id'] == candidate.id for r in skill_results):
                    continue
                
                try:
                    # Get candidate skills
                    db_skills = []
                    if hasattr(candidate, 'candidate_skills'):
                        db_skills = [cs.skill.skill_name for cs in candidate.candidate_skills if cs.skill]
                    
                    # Hitung skill matches
                    matched_count = 0
                    matched_skill_names = []
                    
                    for skill_term in skill_terms:
                        # Cek di skills
                        skill_found = any(skill_term.lower() in s.lower() or s.lower() in skill_term.lower() 
                                         for s in db_skills)
                        
                        # Cek di experience
                        exp_found = skill_term.lower() in (candidate.experience or "").lower()
                        
                        if skill_found or exp_found:
                            matched_count += 1
                            matched_skill_names.append(skill_term)
                    
                    if matched_count > 0:
                        skill_match_ratio = matched_count / len(skill_terms)
                        match_score = int(skill_match_ratio * 100)
                        
                        candidate_data = {
                            "id": candidate.id,
                            "name": candidate.name,
                            "email": candidate.email,
                            "phone": candidate.phone,
                            "match_score": match_score,
                            "matched_skills_count": matched_count,
                            "total_searched_skills": len(skill_terms),
                            "matched_skills": matched_skill_names,
                            "has_role_match": False,
                            "role_matched": ignored_role if ignored_role else None,
                            "status": candidate.status,
                            "skills": db_skills,
                            "experience": getattr(candidate, 'experience', ''),
                            "education": getattr(candidate, 'education', ''),
                            "search_type": "experience_fallback",
                            "match_note": f"Found in experience/skills: {', '.join(matched_skill_names[:3])}" + 
                                          (f" (ignored role: {ignored_role})" if ignored_role else "")
                        }
                        
                        skill_results.append(candidate_data)
                        
                except Exception as e:
                    print(f"❌ Error processing experience candidate {candidate.id}: {e}")
                    continue
        
        # Sort by match score
        skill_results.sort(key=lambda x: x['match_score'], reverse=True)
        
        print(f"✅ Total candidates found: {len(skill_results)}")
        return skill_results
        
    except Exception as e:
        print(f"❌ Error in improved skill-only search: {e}")
        import traceback
        traceback.print_exc()
        return []
    
# app/services/talent_search.py - TAMBAHKAN fungsi ini

def filter_role_candidates_by_skills(role_candidates, skill_terms, closest_role):
    """Filter kandidat role berdasarkan skills match"""
    filtered_results = []
    
    for candidate_data in role_candidates:
        candidate_id = candidate_data['id']
        
        # Get candidate skills
        candidate_skills = get_candidate_skills(candidate_id)
        
        # Hitung skill matches
        matched_skills_count = 0
        matched_skill_names = []
        
        for skill_term in skill_terms:
            for candidate_skill in candidate_skills:
                skill_lower = candidate_skill.lower()
                term_lower = skill_term.lower()
                
                if (term_lower in skill_lower or 
                    skill_lower in term_lower or
                    calculate_string_similarity(term_lower, skill_lower) > 0.7):
                    matched_skills_count += 1
                    matched_skill_names.append(skill_term)
                    break
        
        # Update candidate data
        candidate_data['matched_skills_count'] = matched_skills_count
        candidate_data['total_searched_skills'] = len(skill_terms)
        candidate_data['matched_skills'] = matched_skill_names
        
        if matched_skills_count > 0:
            # Update score untuk yang match skills
            skill_match_ratio = matched_skills_count / len(skill_terms)
            candidate_data['match_score'] = min(100, candidate_data.get('match_score', 0) + (skill_match_ratio * 30))
            candidate_data['search_type'] = 'role_with_skills'
            candidate_data['match_note'] = f"Role: {closest_role} + {matched_skills_count}/{len(skill_terms)} skills matched"
        else:
            candidate_data['search_type'] = 'role_only'
            candidate_data['match_note'] = f"Role match only (no skill match)"
        
        filtered_results.append(candidate_data)
    
    # Sort by match score
    filtered_results.sort(key=lambda x: x['match_score'], reverse=True)
    return filtered_results

# app/services/talent_search.py - TAMBAHKAN fungsi ini

def calculate_string_similarity(str1, str2):
    """Calculate similarity between two strings (simplified version)"""
    if not str1 or not str2:
        return 0
    
    s1 = str1.lower()
    s2 = str2.lower()
    
    if s1 == s2:
        return 1
    
    # Check for substring
    if s1 in s2 or s2 in s1:
        return 0.8
    
    # Simple Jaccard similarity
    set1 = set(s1)
    set2 = set(s2)
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    
    if union == 0:
        return 0
    
    return intersection / union

# ============================
# FUNGSI HELPER BARU
# ============================

# talent_search.py - Tambahkan fungsi ini
# app/services/talent_search.py - TAMBAHKAN fungsi ini

def search_candidates_with_skills(query: str, skills_from_frontend: list):
    """
    Search candidates with skills from frontend
    LOGIKA: Skill-first search - jika role tidak ditemukan, cari berdasarkan skills
    """
    query_lower = query.lower().strip()
    
    # 1. Jika query kosong dan ada skills, lakukan skill-only search
    if not query_lower and skills_from_frontend:
        print(f"🔍 Empty query with skills, doing skill-only search: {skills_from_frontend}")
        return search_by_skills_only(skills_from_frontend)
    
    # 2. Jika query tidak kosong, cek apakah ini nama
    if is_likely_name(query):
        print(f"👤 Detected as NAME search: {query}")
        name_results = search_by_name(query)
        
        # Filter name results by skills jika ada
        if skills_from_frontend and name_results:
            return filter_candidates_by_skills(name_results, skills_from_frontend)
        return name_results
    
    # 3. Cari role dengan fuzzy matching
    closest_role = find_closest_role(query_lower)
    
    # 4. Ekstrak semua kata dari query sebagai potential skills
    all_query_words = re.findall(r'\b\w+\b', query_lower)
    query_skill_terms = [term for term in all_query_words if len(term) >= 2]
    
    # 5. Gabungkan skills dari frontend dan query
    all_skills = skills_from_frontend.copy() if skills_from_frontend else []
    all_skills.extend(query_skill_terms)
    all_skills = list(set(all_skills))  # Remove duplicates
    
    print(f"🔍 Search parameters - Role: {closest_role}, Skills: {all_skills}")
    
    if closest_role:
        role_terms = ROLE_JOB_MAP[closest_role]
        print(f"✅ Role detected: {closest_role} → {role_terms}")
        
        # Filter out role words dari skill terms
        role_words = set(closest_role.split())
        filtered_skills = [term for term in all_skills if term not in role_words]
        
        # 6. Cari kandidat dengan role TERLEBIH DAHULU
        role_results = search_role_only(role_terms, closest_role)
        
        if role_results:
            print(f"✅ Found {len(role_results)} candidates with role '{closest_role}'")
            
            # Jika ada skills, filter role results by skills
            if filtered_skills:
                print(f"🔍 Filtering role candidates by skills: {filtered_skills}")
                return filter_role_candidates_by_skills(role_results, filtered_skills, closest_role)
            else:
                return role_results
        else:
            # 7. FALLBACK: Jika tidak ada kandidat dengan role, cari berdasarkan skills
            print(f"⚠️ No candidates with role '{closest_role}', falling back to SKILL search")
            if filtered_skills:
                skill_results = search_by_skills_only(filtered_skills)
                if skill_results:
                    print(f"✅ Found {len(skill_results)} candidates by skills (role not found)")
                    # Tambahkan note bahwa ini adalah skill-only fallback
                    for result in skill_results:
                        result['search_type'] = 'skill_only_fallback'
                        result['role_matched'] = closest_role
                        result['has_role_match'] = False
                        result['match_note'] = f"Role '{closest_role}' not found. Showing candidates with matching skills: {', '.join(filtered_skills[:3])}"
                    return skill_results
                else:
                    print(f"❌ No candidates found with skills: {filtered_skills}")
                    return []
            else:
                return []
    else:
        # 8. Tidak ada role terdeteksi, lakukan skill-only search
        print(f"🔍 No role detected, doing skill-only search: {all_skills}")
        if all_skills:
            return search_by_skills_only(all_skills)
        else:
            # Jika tidak ada kriteria, return semua kandidat
            print("📊 No criteria, returning all candidates")
            return get_all_candidates()
        
# app/services/talent_search.py - TAMBAHKAN fungsi ini

def filter_candidates_by_skills(candidate_list, skill_terms, search_type="name_with_skills"):
    """Filter list of candidates by skills"""
    filtered_results = []
    
    for candidate_data in candidate_list:
        candidate_id = candidate_data['id']
        
        # Get candidate skills
        candidate_skills = get_candidate_skills(candidate_id)
        
        # Hitung skill matches
        matched_skills_count = 0
        matched_skill_names = []
        
        for skill_term in skill_terms:
            for candidate_skill in candidate_skills:
                skill_lower = candidate_skill.lower()
                term_lower = skill_term.lower()
                
                # Check for skill match
                if (term_lower in skill_lower or 
                    skill_lower in term_lower or
                    calculate_string_similarity(term_lower, skill_lower) > 0.7):
                    matched_skills_count += 1
                    matched_skill_names.append(skill_term)
                    break
        
        if matched_skills_count > 0:
            # Update candidate data dengan skill match info
            candidate_data['matched_skills_count'] = matched_skills_count
            candidate_data['total_searched_skills'] = len(skill_terms)
            candidate_data['matched_skills'] = matched_skill_names
            candidate_data['search_type'] = search_type
            
            # Update match score based on skill match
            skill_match_ratio = matched_skills_count / len(skill_terms)
            candidate_data['match_score'] = min(100, candidate_data.get('match_score', 0) + (skill_match_ratio * 30))
            candidate_data['match_note'] = f"{candidate_data.get('match_note', '')} + {matched_skills_count}/{len(skill_terms)} skills matched"
            
            filtered_results.append(candidate_data)
    
    return filtered_results

def search_role_and_skills(role_terms, skill_terms, closest_role):
    """Cari kandidat dengan BOTH role dan skill match"""
    try:
        # Build conditions
        role_conditions = [func.lower(Candidate.experience).like(f"%{term}%") for term in role_terms]
        skill_conditions = [func.lower(Skill.skill_name).like(f"%{term}%") for term in skill_terms]
        
        query = (
            db.session.query(
                Candidate.id,
                Candidate.name,
                Candidate.email,
                Candidate.phone,
                Candidate.match_score,
                Candidate.experience,
                Candidate.education,
                Candidate.status,
                func.count(Skill.id).label('matched_skills_count')
            )
            .join(CandidateSkill, Candidate.id == CandidateSkill.candidate_id)
            .join(Skill, Skill.id == CandidateSkill.skill_id)
            .filter(and_(
                or_(*role_conditions),
                or_(*skill_conditions)
            ))
            .group_by(
                Candidate.id,
                Candidate.name,
                Candidate.email,
                Candidate.phone,
                Candidate.match_score,
                Candidate.experience,
                Candidate.education,
                Candidate.status
            )
            .order_by(func.count(Skill.id).desc())
            .all()
        )
        
        results = []
        for row in query:
            try:
                # Get candidate skills
                db_skills = get_candidate_skills(row.id)
                
                total_searched = len(skill_terms)
                skill_match_ratio = row.matched_skills_count / total_searched if total_searched > 0 else 0
                
                # Score tinggi untuk BOTH match
                role_match_score = 50  # Role match
                skill_match_score = skill_match_ratio * 50  # Skill match
                overall_match_score = min(100, role_match_score + skill_match_score)
                
                candidate_data = {
                    "id": row.id,
                    "name": row.name,
                    "email": row.email,
                    "phone": row.phone,
                    "match_score": float(overall_match_score),
                    "matched_skills_count": row.matched_skills_count,
                    "total_searched_skills": total_searched,
                    "has_role_match": True,
                    "role_matched": closest_role,
                    "status": row.status,
                    "skills": db_skills,
                    "experience": row.experience,
                    "education": row.education,
                    "search_type": "role_and_skills",
                    "match_note": f"Perfect match: {closest_role} + {row.matched_skills_count}/{total_searched} skills"
                }
                
                results.append(candidate_data)
                
            except Exception as e:
                print(f"❌ Error memproses kandidat {row.id}: {e}")
                continue
        
        return results
        
    except Exception as e:
        print(f"❌ Error in role+skills search: {e}")
        return []

def search_role_only(role_terms, closest_role):
    """Cari kandidat hanya berdasarkan role"""
    try:
        role_conditions = [func.lower(Candidate.experience).like(f"%{term}%") for term in role_terms]
        
        query = (
            db.session.query(
                Candidate.id,
                Candidate.name,
                Candidate.email,
                Candidate.phone,
                Candidate.match_score,
                Candidate.experience,
                Candidate.education,
                Candidate.status
            )
            .filter(or_(*role_conditions))
            .all()
        )
        
        results = []
        for row in query:
            # Get candidate skills
            db_skills = get_candidate_skills(row.id)
            
            candidate_data = {
                "id": row.id,
                "name": row.name,
                "email": row.email,
                "phone": row.phone,
                "match_score": float(row.match_score) if row.match_score else 70.0,
                "matched_skills_count": 0,
                "total_searched_skills": 0,
                "has_role_match": True,
                "role_matched": closest_role,
                "status": row.status,
                "skills": db_skills,
                "experience": row.experience,
                "education": row.education,
                "search_type": "role_only"
            }
            
            results.append(candidate_data)
        
        return results
        
    except Exception as e:
        print(f"❌ Error in role-only search: {e}")
        return []

def get_candidate_skills(candidate_id):
    """Helper function untuk mendapatkan skills kandidat"""
    db_skills = []
    try:
        candidate_skills = CandidateSkill.query.filter_by(candidate_id=candidate_id).all()
        for cs in candidate_skills:
            skill = Skill.query.get(cs.skill_id)
            if skill:
                db_skills.append(skill.skill_name)
    except Exception as e:
        print(f"⚠️ Error getting skills for candidate {candidate_id}: {e}")
    
    return db_skills

# talent_search.py - Tambahkan fungsi untuk experience only search
def search_experience_only(role_terms, closest_role):
    """Cari kandidat hanya berdasarkan experience (tanpa skill)"""
    try:
        role_conditions = [func.lower(Candidate.experience).like(f"%{term}%") for term in role_terms]
        
        query = (
            db.session.query(
                Candidate.id,
                Candidate.name,
                Candidate.email,
                Candidate.phone,
                Candidate.match_score,
                Candidate.experience,
                Candidate.education,
                Candidate.status
            )
            .filter(or_(*role_conditions))
            .all()
        )
        
        results = []
        for row in query:
            # Get candidate skills (untuk display saja)
            db_skills = get_candidate_skills(row.id)
            
            # Hitung years experience dari string experience
            years = extract_years_from_experience(row.experience)
            years_score = calculate_years_score(years)
            
            # Calculate experience match score (di backend juga hitung)
            exp_match_score = calculate_experience_match_score(row.experience, closest_role)
            
            # Final score: 80% experience + 20% years
            final_score = int((exp_match_score * 0.8) + (years_score * 0.2))
            
            candidate_data = {
                "id": row.id,
                "name": row.name,
                "email": row.email,
                "phone": row.phone,
                "match_score": final_score,
                "matched_skills_count": 0,
                "total_searched_skills": 0,
                "has_role_match": True,
                "role_matched": closest_role,
                "years_experience": years,
                "status": row.status,
                "skills": db_skills,
                "experience": row.experience,
                "education": row.education,
                "search_type": "experience_only",
                "match_note": f"Experience match: {closest_role} ({years} years)"
            }
            
            results.append(candidate_data)
        
        # Sort by experience match score
        results.sort(key=lambda x: x['match_score'], reverse=True)
        
        return results
        
    except Exception as e:
        print(f"❌ Error in experience-only search: {e}")
        return []

# Tambahkan helper functions
def extract_years_from_experience(experience):
    """Extract years from experience string"""
    if not experience:
        return 0
    
    # Pattern: (2018-2020) or (2018-Present)
    year_match = re.search(r'\((\d{4})-(\d{4}|Present)\)', experience)
    if year_match:
        start_year = int(year_match.group(1))
        end_year = year_match.group(2)
        if end_year == 'Present':
            end_year = datetime.now().year
        else:
            end_year = int(end_year)
        return max(end_year - start_year, 0)
    
    # Pattern: X years
    years_match = re.search(r'(\d+)\s+years?', experience, re.IGNORECASE)
    if years_match:
        return int(years_match.group(1))
    
    return 0

def calculate_years_score(years):
    """Calculate score based on years of experience (0-100)"""
    if years >= 10:
        return 100
    elif years >= 7:
        return 90
    elif years >= 5:
        return 80
    elif years >= 4:
        return 70
    elif years >= 3:
        return 60
    elif years >= 2:
        return 50
    elif years >= 1:
        return 30
    else:
        return 10

def calculate_experience_match_score(experience, search_role):
    """Calculate experience match score (0-100)"""
    if not experience or not search_role:
        return 0
    
    exp_lower = experience.lower()
    role_lower = search_role.lower()
    
    # Exact match
    if role_lower in exp_lower:
        return 100
    
    # Word-based matching
    exp_words = set(re.findall(r'\b\w+\b', exp_lower))
    role_words = set(re.findall(r'\b\w+\b', role_lower))
    
    if not role_words:
        return 0
    
    # Check for word overlap
    common_words = exp_words.intersection(role_words)
    if common_words:
        match_ratio = len(common_words) / len(role_words)
        return int(match_ratio * 100)
    
    return 0