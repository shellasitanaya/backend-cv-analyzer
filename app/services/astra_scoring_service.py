# app/services/astra_scoring_service.py
import os
import json
import google.generativeai as genai
from typing import Dict, List
import re
from datetime import datetime
from dotenv import load_dotenv

# 1. Load Environment Variables
load_dotenv()
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")

# 2. Configure Gemini
if GENAI_API_KEY:
    genai.configure(api_key=GENAI_API_KEY)
else:
    print("\033[91m⚠️ FATAL ERROR: GEMINI_API_KEY not found in .env file\033[0m") 

def get_best_available_model():
    """Auto-detect model terbaik."""
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        priority_list = [
            'models/gemini-2.5-flash', 
            'models/gemini-2.0-flash', 
            'models/gemini-1.5-pro',
            'models/gemini-1.5-flash', 
            'models/gemini-pro'
        ]
        for model_name in priority_list:
            if model_name in available_models: return model_name
        return available_models[0] if available_models else 'models/gemini-pro'
    except: return 'models/gemini-1.5-flash'

class AstraScoringService:
    """
    Service penilaian CV dengan:
    1. STABILIZED BALANCED LOGIC (Skor Mahasiswa Adil).
    2. Smart Filtering (Noise Cancellation Wajib).
    3. Direct 'You' Communication Style.
    4. Flexible Major Logic.
    Output: ALWAYS ENGLISH.
    """

    @staticmethod
    def analyze_cv_with_gemini(cv_text: str, job_desc_text: str, job_title: str = "General Job") -> Dict:
        if not GENAI_API_KEY: return {"error": "API Key Error"}

        current_year = datetime.now().year

        # --- LOGGING ---
        print("\n" + "="*70)
        print(f"🚀 [AI SMART ANALYZER] Processing: {job_title}")
        print("="*70)

        # --- PROMPT: THE HYBRID STABLE VERSION ---
        prompt = f"""
        Act as a Supportive Career Coach & Technical Recruiter.
        Your goal is to evaluate the candidate's POTENTIAL FAIRLY based on evidence, treating academic projects as real experience.
        
        **CRITICAL STYLE RULES:**
        1. **SPEAK TO THE USER:** Use "You", "Your", "Your experience".
        2. **FORBIDDEN WORDS:** Do NOT use "The candidate", "This candidate", "He", "She".
        3. **TONE:** Constructive, encouraging, yet professional.

        === JOB REQUIREMENT ===
        POSITION: {job_title}
        JD: "{job_desc_text}"
        CURRENT YEAR: {current_year}

        === CANDIDATE CV ===
        {cv_text[:45000]}

        === INSTRUCTIONS (STRICT EXECUTION ORDER) ===

        **STEP 1: NOISE CANCELLATION (CRITICAL)**
        - **IGNORE IRRELEVANT WORK:** If the candidate has non-tech work (e.g., Sales, Admin) and applies for Tech, **DO NOT** let it lower their score.
        - **FOCUS ONLY ON:** Coding Projects, IT Organizations, Internships, and Academic Capstones.
        - *Treat "Head of IT Division" in an organization as VALID Leadership Experience.*

        **STEP 2: MANDATORY CHECKS (GATEKEEPER)**
           **A. EDUCATION LEVEL**:
             - Internship Mode + Student = PASS.
             - Professional Mode + Student = FAIL.
             - *Reasoning:* "As an active student, you are..."
           
           **B. MAJOR RELEVANCE (CONDITIONAL)**:
             - **Check JD:** Does it explicitly say "Must be S1 Informatics" or similar?
             - **LOGIC:**
               1. IF JD IS SPECIFIC: Candidate Major MUST match.
               2. IF JD IS OPEN/SILENT: **STATUS: PASS** for everyone.
             - *Reasoning:* "The job requirement regarding major is..."

           **C. GPA / IPK**:
             - Check against requirement.
           
           **D. Experience Duration**:
             - Internship Mode -> 0 years is PASS.

        **STEP 3: SCORING RUBRIC (TOTAL 100.00)**:
           
           **A. Hard Skill Relevance (60%)**
           - **Student Rule:** Academic projects using the tool (e.g., "Python for Data Mining class") COUNT as valid experience. 
           - **Action:** If the tool matches the JD, give a HIGH SCORE in this section.
           
           **B. Seniority & Experience (20%) - STUDENT ADJUSTED:**
           - **0-40:** No projects, no relevant organizations.
           - **40-70:** Passive member or simple academic assignments.
           - **70-85:** Active Leadership (Coordinator/Head) OR Internship Experience OR Winning Competitions. (TARGET FOR ACTIVE STUDENTS).
           - **85-100:** Proven Professional Work Experience (>1 year).

           **C. Description Quality (20%) - STUDENT ADJUSTED:**
           - **Low:** Lists only.
           - **Medium:** "I built a website."
           - **High:** "Built a website using Laravel, handled 200 users, improved X." (Even if it's a student project, rate this HIGH).

        **STEP 4: SKILL EVIDENCE (BALANCED 4-TIER)**
        1. **Strong Evidence (Score: 9.0 - 10.0)**
           - Tech Details + Metrics. *Ex: "You reduced query time by 30%."*
        2. **Moderate Evidence (Score: 7.0 - 8.9)**
           - Tech Details OR Deep Explanation. *Ex: "You built an app using Laravel and OOP."*
        3. **Standard Context (Score: 4.0 - 6.9)**
           - Narrative mentions usage. *Ex: "You used Python."*
        4. **Listed Only (Score: 1.0 - 3.9)**
           - List only.
        5. **Missing (Score: 0)**
           - Not found.

        === ADVICE GENERATION ===
        - Provide actionable advice to move up one tier using "You".

        === OUTPUT JSON FORMAT (ENGLISH ONLY) ===
        {{
            "candidate_summary": "2 sentences summary focusing on relevant strengths (Use 'You').",
            "mandatory_checks": {{
                "gpa": {{ "value": "Original", "converted_value": "Normalized", "status": "PASS/FAIL/NOTE", "reason": "Direct reasoning using 'You'..." }},
                "major": {{ "value": "Major Name", "status": "PASS/FAIL", "reason": "Direct reasoning using 'You'..." }},
                "experience_years": {{ "value": "Years", "status": "PASS/FAIL", "reason": "Direct reasoning using 'You'..." }},
                "education_level": {{ "value": "Degree Status", "status": "PASS/FAIL", "reason": "Direct reasoning using 'You'..." }}
            }},
            "rubric_scores": {{
                "relevance_raw": 0.0, "seniority_raw": 0.0, "quality_raw": 0.0
            }},
            "skills_analysis": [
                {{ "skill": "Name", "level": "Strong Evidence/Moderate Evidence/Standard Context/Listed Only/Missing", "score": 8.5, "reason": "Direct advice using 'You'..." }}
            ],
            "suggestion": "Strategic advice (Use 'You'). If irrelevant jobs found: 'Consider removing [Job]...'"
        }}
        """

        try:
            model_name = get_best_available_model()
            print(f"Using Model: {model_name}")
            model = genai.GenerativeModel(model_name)
            
            response = model.generate_content(
                prompt, 
                generation_config={"response_mime_type": "application/json", "temperature": 0.0}
            )
            result = json.loads(response.text)

            # --- PYTHON CALCULATION ---
            rubric = result.get('rubric_scores', {})
            
            # Hitung Bobot
            raw_rel = float(rubric.get('relevance_raw', 0))
            raw_sen = float(rubric.get('seniority_raw', 0))
            raw_qua = float(rubric.get('quality_raw', 0))

            weighted_rel = raw_rel * 0.60
            weighted_sen = raw_sen * 0.20
            weighted_qua = raw_qua * 0.20
            
            final_score = weighted_rel + weighted_sen + weighted_qua
            final_score = min(100.0, final_score)

            # --- MANDATORY PENALTY ---
            mandatory = result.get('mandatory_checks', {})
            is_failed = False
            fail_reasons = []
            
            if mandatory.get('gpa', {}).get('status') == 'FAIL':
                is_failed = True; fail_reasons.append("Low GPA")
            
            # [LOGIKA BARU] Conditional Major Check
            if mandatory.get('major', {}).get('status') == 'FAIL':
                is_failed = True; fail_reasons.append("Irrelevant Major")
                
            if mandatory.get('experience_years', {}).get('status') == 'FAIL':
                is_failed = True; fail_reasons.append("Insufficient Experience")
            if mandatory.get('education_level', {}).get('status') == 'FAIL':
                is_failed = True; fail_reasons.append("Education Level Mismatch")

            if is_failed:
                final_score = min(final_score, 25.0) 
                print(f"⛔ GATEKEEPER FAILED (Score Capped at 25%): {', '.join(fail_reasons)}")

            # --- LOGGING TO TERMINAL ---
            print(f"\n📊 RUBRIC CALCULATION:")
            print(f"   1. Relevance  (60%): {raw_rel:>5.1f} -> {weighted_rel:>5.1f}")
            print(f"   2. Seniority  (20%): {raw_sen:>5.1f} -> {weighted_sen:>5.1f}")
            print(f"   3. Quality    (20%): {raw_qua:>5.1f} -> {weighted_qua:>5.1f}")
            
            gpa_info = mandatory.get('gpa', {})
            print(f"\n🎓 GPA CHECK:")
            print(f"   - Status   : {gpa_info.get('status')} ({gpa_info.get('value')})")
            
            print(f"\n🏁 FINAL SCORE : {final_score:.2f}%")
            print("="*70 + "\n")

            # Update structure for frontend
            result['rubric_scores'] = {
                "relevance_score": weighted_rel,
                "seniority_score": weighted_sen,
                "quality_score": weighted_qua
            }

            return {
                "lulus": final_score >= 60,
                "skor_akhir": round(final_score, 2),
                "ai_analysis": result,
                "job_info": {"title": job_title, "description": job_desc_text}
            }

        except Exception as e:
            print(f"❌ Gemini Error: {e}")
            return {"lulus": False, "skor_akhir": 0, "error": str(e), "job_info": {"title": job_title}}