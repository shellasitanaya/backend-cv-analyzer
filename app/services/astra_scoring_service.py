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
    print("\033[91m⚠ FATAL ERROR: GEMINI_API_KEY tidak ditemukan di file .env\033[0m")

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
        print(f"🚀 [ASTRA SMART ANALYZER] Processing: {job_title}")
        print("="*70)

        # --- PROMPT: ALWAYS ENGLISH ---
        prompt = f"""
        Act as a Global Senior Recruiter & Career Coach.
        Your goal is to evaluate the candidate based on specific criteria with HIGH PRECISION.
        
        *CRITICAL RULE:* ALL OUTPUT MUST BE IN *ENGLISH*, regardless of the CV language.

        === JOB REQUIREMENT ===
        POSITION: {job_title}
        JD: "{job_desc_text}"
        CURRENT YEAR: {current_year}

        === CANDIDATE CV ===
        {cv_text[:35000]}

        === INSTRUCTIONS ===

        1. *MANDATORY CHECKS (SMART GATEKEEPER)*:
           - *Education Degree*: Check minimum degree (S1/D3). Higher degree is PASS. "Student" status is FAIL.
           - *GPA / IPK (SMART VALIDATION)*:
             a. Identify Job Scale (Default 4.00 if not stated).
             b. Identify Candidate Scale (Infer 10.0 if > 4.0).
             c. Normalize: (Candidate_Val / Candidate_Scale) * Job_Scale.
             d. Evaluate: Fail if < Required. Pass if not found (with note).
           - *Relevant Experience*: Count ONLY relevant years. Fail if < Required.
           - *Major*: Check semantic relevance (e.g. IT == CS).

        2. *SCORING RUBRIC (TOTAL 100.00)*:
           Rate each category on a scale of 0-100. Do not round up.
           
           *A. Hard Skill Relevance (60%)*
           - How many required hard skills are present & relevant?
           - Score 0-100 based on coverage & depth.
           
           *B. Seniority & Context (20%)*
           - Does experience duration & role depth match?
           - Score 0-100.

           *C. Description Quality (20%)*
           - Use of Action Verbs & Quantitative Metrics ("20% growth").
           - Score 0-100.

        === SKILL ANALYSIS INSTRUCTIONS ===
        For each required skill, assign a *"Proof Level"*:
        - *"Strong Evidence"*: Found in Work Experience with context/metrics.
        - *"Standard Context"*: Found in Work Experience but generic.
        - *"Listed Only"*: Found in Skills list only.
        - *"Missing"*: Not found.

        === OUTPUT JSON FORMAT (ENGLISH ONLY) ===
        {{
            "candidate_summary": "2 sentences summary of candidate potential.",
            "mandatory_checks": {{
                "gpa": {{ 
                    "value": "Original Value", 
                    "converted_value": "Normalized Value",
                    "status": "PASS/FAIL/NOTE", 
                    "reason": "Explanation of conversion or status." 
                }},
                "major": {{ "value": "Major Name", "status": "PASS/FAIL", "reason": "..." }},
                "experience_years": {{ "value": "Number of Years", "status": "PASS/FAIL", "reason": "..." }},
                "education_level": {{ "value": "Degree Level", "status": "PASS/FAIL", "reason": "..." }}
            }},
            "rubric_scores": {{
                "relevance_raw": 0.0,  
                "seniority_raw": 0.0, 
                "quality_raw": 0.0
            }},
            "skills_analysis": [
                {{ 
                    "skill": "Skill Name", 
                    "level": "Strong Evidence/Standard Context/Listed Only/Missing", 
                    "score": 10.0, 
                    "reason": "Specific advice to improve this skill section." 
                }}
            ],
            "suggestion": "Main strategic advice for the candidate."
        }}
        """

        try:
            model_name = get_best_available_model()
            print(f"🤖 Using Model: {model_name}")
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
            
            # Cek Fail
            if mandatory.get('gpa', {}).get('status') == 'FAIL':
                is_failed = True; fail_reasons.append("GPA Low")
            if mandatory.get('major', {}).get('status') == 'FAIL':
                is_failed = True; fail_reasons.append("Irrelevant Major")
            if mandatory.get('experience_years', {}).get('status') == 'FAIL':
                is_failed = True; fail_reasons.append("Experience Short")
            if mandatory.get('education_level', {}).get('status') == 'FAIL':
                is_failed = True; fail_reasons.append("Education Mismatch")

            if is_failed:
                final_score = min(final_score, 25.0) # Penalty keras
                print(f"⛔ GATEKEEPER FAILED: {fail_reasons}")

            # --- LOGGING TO TERMINAL ---
            print(f"\n📊 RUBRIC CALCULATION:")
            print(f"   1. Relevance  (60%): {raw_rel:>5.1f} -> {weighted_rel:>5.1f}")
            print(f"   2. Seniority  (20%): {raw_sen:>5.1f} -> {weighted_sen:>5.1f}")
            print(f"   3. Quality    (20%): {raw_qua:>5.1f} -> {weighted_qua:>5.1f}")
            
            gpa_info = mandatory.get('gpa', {})
            print(f"\n🎓 GPA CHECK:")
            print(f"   - Original : {gpa_info.get('value')}")
            print(f"   - Normalized: {gpa_info.get('converted_value')}")
            print(f"   - Status   : {gpa_info.get('status')}")
            
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