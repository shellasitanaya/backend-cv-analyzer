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
    print("\033[91m⚠️ FATAL ERROR: GEMINI_API_KEY tidak ditemukan di file .env\033[0m")

def get_best_available_model():
    """Auto-detect model terbaik (Prioritas Gemini 2.5)."""
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # PRIORITAS BARU: Gemini 2.5 -> 2.0 -> 1.5
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
    Service penilaian CV berbasis Rubrik 60/20/20.
    Logika: AI memberi nilai mentah (0-100), Python menghitung bobot.
    """

    @staticmethod
    def analyze_cv_with_gemini(cv_text: str, job_desc_text: str, job_title: str = "General Job") -> Dict:
        if not GENAI_API_KEY: return {"error": "API Key Error"}

        current_year = datetime.now().year

        # --- LOGGING ---
        print("\n" + "="*70)
        print(f"🚀 [ASTRA OPTIMIZER] ANALYZING: {job_title}")
        print("="*70)

        # --- PROMPT: LOGIC FIX (SCORE 0-100 PER CATEGORY) ---
        prompt = f"""
        Act as a Senior CV Consultant & Optimizer.
        Your goal is to audit the QUALITY of the candidate's CV based on the Job Description.

        === JOB TARGET ===
        POSITION: {job_title}
        JD: "{job_desc_text}"
        CURRENT YEAR: {current_year}

        === CANDIDATE CV ===
        {cv_text[:40000]}

        === SCORING INSTRUCTIONS (CRITICAL) ===
        Rate each category on a scale of **0 to 100**.
        
        1. **Relevance (0-100)**: 
           - How many required hard skills are present? 
           - Are they backed by project context?
           - *Example:* 80/100 means strong match but missing 1-2 niche skills.
        
        2. **Seniority (0-100)**:
           - Does experience duration match the role?
           - Does the candidate show career progression?
           - *Example:* 100/100 means perfect seniority match. 50/100 means too junior.

        3. **Quality (0-100)**:
           - Usage of Action Verbs ("Led", "Built") vs Passive ("Helped").
           - Usage of Numbers/Metrics ("Improved by 20%").
           - *Example:* 60/100 means good content but lacks numbers.

        === SKILL ANALYSIS INSTRUCTIONS ===
        For each required skill, assign a **"Proof Level"**:
        - **"Strong Evidence"**: Found in Work Experience with context/metrics.
        - **"Standard Context"**: Found in Work Experience but generic.
        - **"Listed Only"**: Found in Skills list only.
        - **"Missing"**: Not found.

        === OUTPUT JSON FORMAT ===
        {{
            "candidate_summary": "Ringkasan audit CV 2 kalimat (Bahasa Indonesia).",
            "mandatory_checks": {{
                "gpa": {{ "value": "Angka/Not Listed", "status": "PASS/NOTE" }},
                "major": {{ "value": "Nama Jurusan", "status": "PASS/FAIL" }},
                "experience_years": {{ "value": "Angka", "status": "PASS/FAIL" }}
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
                    "reason": "Saran perbaikan spesifik (Bahasa Indonesia)." 
                }}
            ],
            "suggestion": "Strategi optimasi utama."
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

            # --- PYTHON CALCULATION (The Real Logic) ---
            rubric = result.get('rubric_scores', {})
            
            # Ambil Raw Score (0-100) dari AI
            raw_rel = float(rubric.get('relevance_raw', 0))
            raw_sen = float(rubric.get('seniority_raw', 0))
            raw_qua = float(rubric.get('quality_raw', 0))

            # Hitung Bobot (Weighted Score)
            weighted_rel = raw_rel * 0.60  # Bobot 60%
            weighted_sen = raw_sen * 0.20  # Bobot 20%
            weighted_qua = raw_qua * 0.20  # Bobot 20%
            
            # Total Score
            final_score = weighted_rel + weighted_sen + weighted_qua
            final_score = min(100.0, final_score)

            # --- MANDATORY PENALTY ---
            mandatory = result.get('mandatory_checks', {})
            is_failed = False
            fail_reasons = []
            
            if mandatory.get('major', {}).get('status') == 'FAIL':
                is_failed = True; fail_reasons.append("Jurusan Tidak Relevan")
            if mandatory.get('experience_years', {}).get('status') == 'FAIL':
                is_failed = True; fail_reasons.append("Pengalaman Kurang")

            if is_failed:
                final_score = min(final_score, 30.0) # Penalty keras
                print(f"⛔ GATEKEEPER: Failed due to {fail_reasons}")

            # --- LOGGING TO TERMINAL ---
            print(f"\n📊 RUBRIC CALCULATION:")
            print(f"   1. Relevansi  (60%): {raw_rel:>5.1f} x 0.6 = {weighted_rel:>5.1f}")
            print(f"   2. Senioritas (20%): {raw_sen:>5.1f} x 0.2 = {weighted_sen:>5.1f}")
            print(f"   3. Kualitas   (20%): {raw_qua:>5.1f} x 0.2 = {weighted_qua:>5.1f}")
            print(f"   ---------------------------------------")
            print(f"   🏁 FINAL SCORE     : {final_score:>5.1f}%")
            print("="*70 + "\n")

            # Update result structure untuk frontend (kirim nilai terbobot agar bar chart sesuai)
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