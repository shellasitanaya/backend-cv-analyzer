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
    1. ADAPTIVE SCORING (Bisa membedakan Student vs Pro).
    2. Smart Filtering (Noise Cancellation).
    3. Direct 'You' Communication Style.
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

        # --- PROMPT: ADAPTIVE PROFESSIONAL VERSION ---
        prompt = f"""
        Act as a Senior Technical Recruiter & Career Coach.
        Your goal is to evaluate the candidate's FIT based on the Job Description, ADAPTING your criteria based on their seniority level.
        
        **CRITICAL STYLE RULES:**
        1. **SPEAK TO THE USER:** Use "You", "Your".
        2. **FORBIDDEN WORDS:** Do NOT use "The candidate", "He", "She".
        3. **TONE:** Professional, objective, and constructive.

        === JOB REQUIREMENT ===
        POSITION: {job_title}
        JD: "{job_desc_text}"
        CURRENT YEAR: {current_year}

        === CANDIDATE CV ===
        {cv_text[:45000]}

        === INSTRUCTIONS (STRICT EXECUTION ORDER) ===

        **STEP 1: PROFILE DETECTION & NOISE CANCELLATION**
        - **DETECT PROFILE:** Is this candidate a **STUDENT/FRESH GRAD** (< 1 year exp) or a **PROFESSIONAL** (> 1 year exp)?
        - **NOISE CANCELLATION:** - If PROFESSIONAL: Ignore student organizations. FOCUS heavily on work history (BSI, Astra, Kopnuspos, etc.).
          - If STUDENT: Treat Organizations & Academic Projects as main experience.
          - **ALWAYS:** Ignore irrelevant jobs (e.g., Waiter/Sales) if applying for Tech/ERP.

        **STEP 2: MANDATORY CHECKS**
           **A. EDUCATION LEVEL**:
             - Internship Job + Student = PASS.
             - Professional Job + Student = FAIL (Unless they are final year/ready to work fulltime).
           
           **B. MAJOR RELEVANCE (CONDITIONAL)**:
             - IF JD specifies "Must be S1 Informatics/System Information": Check strict match.
             - IF JD is open: PASS for everyone.

           **C. GPA / IPK**:
             - Check against requirement.
           
           **D. Experience Duration**:
             - Compare Candidate's **RELEVANT** Work Duration vs JD Requirement.
             - *Note: Overlapping dates (working two jobs) count as valid parallel experience.*

        **STEP 3: SCORING RUBRIC (TOTAL 100.00)**:
           
           **A. Hard Skill Relevance (60%)**
           - Check for specific tools in JD (e.g., ERP, Odoo, SAP, SQL, BPMN).
           - **CRITICAL:** If candidate has mapped Business Processes or used ERP tools (Odoo/SAP) as requested, Score HIGH.
           
           **B. Seniority & Experience (20%) - ADAPTIVE LOGIC (CRITICAL):**
           - **PATH A: PROFESSIONAL (Has Work Exp > 1 Year):**
             - **90-100:** RELEVANT Work Experience >= JD Required Years. (e.g., JD asks 3 years, Candidate has 4 years in ERP/BA -> Score 100).
             - **75-89:** Relevant experience but slightly under years (e.g., 2 years for 3 year role).
             - **50-74:** Experience exists but in a different domain (e.g., Developer applying for Analyst).
           
           - **PATH B: STUDENT/INTERN (Has Work Exp < 1 Year):**
             - **90-100:** Active Leadership (Coordinator/Head) OR Strong Portfolio.
             - **70-89:** Member of Org OR Academic Projects.

           **C. Description Quality (20%) - ADAPTIVE LOGIC:**
           - **Professional:** Look for "Business Value". (e.g., "Improved process by X%", "Managed ERP implementation"). If present -> Score HIGH.
           - **Student:** Look for "Technical Detail". (e.g., "Used Python to...").

        **STEP 4: SKILL EVIDENCE (4-TIER)**
        1. **Strong Evidence (9.0 - 10.0)**
           - Tech Details + Metrics/Impact. *Ex: "You handled ERP implementation for 2 companies."*
        2. **Moderate Evidence (7.0 - 8.9)**
           - Tech Details/Deep Process Explanation. *Ex: "You analyzed business processes using BPMN and Flowcharts."*
        3. **Standard Context (4.0 - 6.9)**
           - Mentioned usage. *Ex: "You used Odoo."*
        4. **Listed Only (1.0 - 3.9)**
           - List only.
        5. **Missing (0)**
           - Not found.

        === ADVICE GENERATION ===
        - Provide actionable advice to move up one tier using "You".

        === OUTPUT JSON FORMAT (ENGLISH ONLY) ===
        {{
            "candidate_summary": "2 sentences summary focusing on relevant strengths (Use 'You').",
            "mandatory_checks": {{
                "gpa": {{ "value": "Original", "converted_value": "Normalized", "status": "PASS/FAIL/NOTE", "reason": "Direct reasoning using 'You'..." }},
                "major": {{ "value": "Major Name", "status": "PASS/FAIL", "reason": "Direct reasoning using 'You'..." }},
                "experience_years": {{ "value": "Total Relevant Years", "status": "PASS/FAIL", "reason": "Direct reasoning using 'You'..." }},
                "education_level": {{ "value": "Degree Status", "status": "PASS/FAIL", "reason": "Direct reasoning using 'You'..." }}
            }},
            "rubric_scores": {{
                "relevance_raw": 0.0, "seniority_raw": 0.0, "quality_raw": 0.0
            }},
            "skills_analysis": [
                {{ "skill": "Name", "level": "Strong Evidence/Moderate Evidence/Standard Context/Listed Only/Missing", "score": 8.5, "reason": "Direct advice using 'You'..." }}
            ],
            "suggestion": "Strategic advice (Use 'You')."
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
            
            # Conditional Major Check
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