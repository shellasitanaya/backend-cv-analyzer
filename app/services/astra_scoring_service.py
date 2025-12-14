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

        # --- PROMPT: ADAPTIVE LOGIC + DIRECT ACTIONABLE ADVICE ---
        prompt = f"""
        Act as a Global Senior Recruiter & Career Coach.
        Your goal is to evaluate the candidate based on specific criteria with HIGH PRECISION.
        
        **CRITICAL RULE:** ALL OUTPUT MUST BE IN **ENGLISH**, regardless of the CV language.

        === JOB REQUIREMENT ===
        POSITION: {job_title}
        JD: "{job_desc_text}"
        CURRENT YEAR: {current_year}

        === CANDIDATE CV ===
        {cv_text[:45000]}

        === INSTRUCTIONS ===

        1. **MANDATORY CHECKS (SMART GATEKEEPER)**:
           - **Education Degree**: Check minimum degree. Higher degree is PASS. 
             **CRITICAL STUDENT RULE:** If position is 'Intern', 'Magang', 'Trainee' -> Active Student status is **PASS**.
             If position is 'Full-time'/'Senior' -> Active Student status is **FAIL**.
           - **GPA / IPK**:
             a. Identify Job Scale (Default 4.00).
             b. Identify Candidate Scale (Infer 10.0 if > 4.0).
             c. Normalize.
             d. Evaluate: Fail if < Required. Pass if not found.
           - **Experience**: Fail only if Actual < Required.

        2. **SCORING RUBRIC (TOTAL 100.00)**:
           *Rate each category on a scale of 0-100.*
           
           **A. Hard Skill Relevance (60%)**
           - Does the candidate have the tools/tech stack required? 
           - For Interns: Coursework/Projects count as valid skill proof.
           
           **B. Seniority & Experience (20%) - CONTEXT AWARE:**
           - **IF INTERN/JUNIOR ROLE:** Do NOT look for years of work. Look for: Organizational experience, Projects, Competitions, or Previous Internships. 
             (Score 90-100 if they have strong projects/org experience).
           - **IF SENIOR ROLE:** Look for years of professional experience matching the JD.

           **C. Description Quality (20%)**
           - Use of Action Verbs & Numbers.
           - For Interns: "Managed event budget" or "Led student team" counts as metrics.

        === SKILL ANALYSIS INSTRUCTIONS (CRITICAL FOR ADVICE STYLE) ===
        For each required skill:
        1. Assign a **"Proof Level"**:
           - **"Strong Evidence"**: Found in Work Experience OR **Academic Projects** with context.
           - **"Standard Context"**: Found but generic.
           - **"Listed Only"**: Found in list only.
           - **"Missing"**: Not found.
        
        2. **WRITE THE REASON/ADVICE IN IMPERATIVE MOOD (DIRECT COMMAND):**
           - **DO NOT** use third person like "The candidate should..." or "He needs to...".
           - **DO** speak directly to the user. Use action verbs.
           - **BAD:** "The candidate provides good evidence but lacks metrics."
           - **GOOD:** "Add specific metrics to your Python project (e.g., 'Reduced processing time by 20%')."
           - **GOOD:** "Move your SQL skill from the list to the Experience section by describing a specific query you wrote."

        === OUTPUT JSON FORMAT (ENGLISH ONLY) ===
        {{
            "candidate_summary": "2 sentences summary.",
            "mandatory_checks": {{
                "gpa": {{ "value": "Original", "converted_value": "Normalized", "status": "PASS/FAIL/NOTE", "reason": "..." }},
                "major": {{ "value": "Major Name", "status": "PASS/FAIL", "reason": "..." }},
                "experience_years": {{ "value": "Years", "status": "PASS/FAIL", "reason": "..." }},
                "education_level": {{ "value": "Level", "status": "PASS/FAIL", "reason": "..." }}
            }},
            "rubric_scores": {{
                "relevance_raw": 0.0,  
                "seniority_raw": 0.0, 
                "quality_raw": 0.0
            }},
            "skills_analysis": [
                {{ "skill": "Name", "level": "Strong Evidence/Standard Context/Listed Only/Missing", "score": 10.0, "reason": "Direct actionable advice (Imperative)." }}
            ],
            "suggestion": "Main strategic advice for the candidate."
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
                final_score = min(final_score, 25.0) # Penalty
                print(f"⛔ GATEKEEPER FAILED (Score Capped): {', '.join(fail_reasons)}")

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