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
    Service penilaian CV dengan Smart GPA Validation, Rubrik 60/20/20, dan Gatekeeper.
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

        # --- PROMPT: IMPROVED TONE & LOGIC ---
        prompt = f"""
        Act as a Professional Technical Recruiter.
        Your goal is to evaluate the candidate with HIGH PRECISION and provide Direct, Constructive Feedback.
        
        **CRITICAL RULE:** ALL OUTPUT MUST BE IN **ENGLISH**.

        === JOB REQUIREMENT ===
        POSITION: {job_title}
        JD: "{job_desc_text}"
        CURRENT YEAR: {current_year}

        === CANDIDATE CV ===
        {cv_text[:45000]}

        === INSTRUCTIONS ===

        1. **MANDATORY CHECKS (SMART GATEKEEPER)**:
           
           **A. EDUCATION LEVEL & STATUS (STRICT)**:
             Step 1: **DETECT JOB MODE**:
               - IF Title/JD contains: "Intern", "Internship", "Magang", "Apprentice", "Trainee" -> Mode is **INTERNSHIP**.
               - ELSE -> Mode is **PROFESSIONAL** (Default).

             Step 2: **EVALUATE CANDIDATE**:
               - Check if candidate is an **Active Student** (Keywords: "Present", "Now", "Expected Graduation", "Mahasiswa", "Semester").
               - **LOGIC:**
                 - IF Mode **PROFESSIONAL** AND Candidate is **Active Student** -> **STATUS: FAIL**.
                 - IF Mode **INTERNSHIP** AND Candidate is **Active Student** -> **STATUS: PASS**.
               
               **REASONING STYLE:**
               - **If FAIL:** Address the user directly. E.g., "Full-time professional roles require a completed degree. As an active student, you are eligible for internships, but not for this full-time position."
               - **DO NOT** use "The candidate is...". Use "You are..." or "Your status...".

           **B. MAJOR RELEVANCE (BROAD IT SPECTRUM)**:
             - **Standard:** Major must relate to the Job Function.
             - **IT EXCEPTION (CRITICAL):** For Software Engineering / Developer roles, degrees in **Data Science, Information Systems, Informatics, Computer Engineering, and Cyber Security** are considered **RELEVANT (PASS)**.
             - **If PASS:** "Your major in [Major Name] provides a relevant technical foundation for this role."

           **C. GPA / IPK**:
             - Identify Scale (4.0/10.0), Normalize, and Evaluate.
             - **If FAIL:** "Your GPA is below the standard requirement for this competitive role."

           **D. Experience Duration**:
             - Fail only if Actual Relevant Years < Required Years.
             - **If FAIL:** "This role requires [X] years of experience. Your current profile highlights primarily academic or leadership experience."

        2. **SCORING RUBRIC (TOTAL 100.00)**:
           
           **A. Hard Skill Relevance (60%)**
           - Does the candidate have the tools/tech stack required? (Mismatching stack = Low Score).
           
           **B. Seniority & Experience (20%) - CONTEXT AWARE:**
           - **IF INTERNSHIP:** Look for Projects, Org Exp. (Score high if present).
           - **IF PROFESSIONAL:** Look for **Professional Work Experience** matching the JD.

           **C. Description Quality (20%)**
           - Use of Action Verbs & Numbers.

        === SKILL ANALYSIS INSTRUCTIONS ===
        For each required skill:
        1. Assign a **"Proof Level"**: "Strong Evidence", "Standard Context", "Listed Only", "Missing".
        2. **ADVICE STYLE:** Use IMPERATIVE MOOD (Direct Command). Speak to the user.
           - E.g., "Add specific metrics to your project...", "Describe your experience with..."

        === OUTPUT JSON FORMAT (ENGLISH ONLY) ===
        {{
            "candidate_summary": "2 sentences summary.",
            "mandatory_checks": {{
                "gpa": {{ "value": "Original", "converted_value": "Normalized", "status": "PASS/FAIL/NOTE", "reason": "Direct explanation to user." }},
                "major": {{ "value": "Major Name", "status": "PASS/FAIL", "reason": "Direct explanation to user." }},
                "experience_years": {{ "value": "Years", "status": "PASS/FAIL", "reason": "Direct explanation to user." }},
                "education_level": {{ "value": "Degree Status", "status": "PASS/FAIL", "reason": "Direct explanation to user." }}
            }},
            "rubric_scores": {{
                "relevance_raw": 0.0,  
                "seniority_raw": 0.0, 
                "quality_raw": 0.0
            }},
            "skills_analysis": [
                {{ "skill": "Name", "level": "...", "score": 10.0, "reason": "Direct advice." }}
            ],
            "suggestion": "Strategic advice."
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
            if mandatory.get('major', {}).get('status') == 'FAIL':
                is_failed = True; fail_reasons.append("Irrelevant Major")
            if mandatory.get('experience_years', {}).get('status') == 'FAIL':
                is_failed = True; fail_reasons.append("Insufficient Experience")
            if mandatory.get('education_level', {}).get('status') == 'FAIL':
                is_failed = True; fail_reasons.append("Education Level Mismatch")

            if is_failed:
                # Logika Capped Score:
                # Jika skor asli >= 25, turunkan jadi 25.
                # Jika skor asli < 25, biarkan apa adanya (jangan dinaikkan).
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