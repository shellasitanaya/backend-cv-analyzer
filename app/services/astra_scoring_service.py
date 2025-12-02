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
    """Auto-detect model terbaik (Flash atau Pro)."""
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Prioritas: Model 2.0 (Cerdas & Cepat) -> 1.5 -> Pro
        priority_list = [
            'models/gemini-2.0-flash',
            'models/gemini-2.5-flash', 
            'models/gemini-1.5-flash', 
            'models/gemini-pro'
        ]
        for model_name in priority_list:
            if model_name in available_models: return model_name
        return available_models[0] if available_models else 'models/gemini-pro'
    except: return 'models/gemini-1.5-flash'

class AstraScoringService:
    @staticmethod
    def analyze_cv_with_gemini(cv_text: str, job_desc_text: str, job_title: str = "General Job") -> Dict:
        if not GENAI_API_KEY: return {"error": "API Key Error"}

        current_year = datetime.now().year

        # --- PROMPT: RUBRIK PENILAIAN BARU (60/20/20) ---
        prompt = f"""
        Act as a Fair & Objective Senior Recruiter. 
        Your goal is to evaluate the candidate based on specific criteria.

        === JOB REQUIREMENT ===
        POSITION: {job_title}
        JD: "{job_desc_text}"
        CURRENT YEAR: {current_year}

        === CANDIDATE CV ===
        {cv_text[:25000]}

        === INSTRUCTIONS ===

        1. **MANDATORY CHECKS (GERBANG LOGIKA)**:
           - **Education Degree**: Check if the candidate meets the minimum degree (e.g., Bachelor/S1).
             - *Rule:* If candidate has a HIGHER degree (e.g., Master/S2) than required, mark as **PASS** (Overqualified is OK).
             - *Rule:* If candidate is still a student/has not graduated, mark as **FAIL** (unless JD allows students).
           - **GPA/IPK**: Extract exact number (e.g. 3.00). 
             - *Rule:* If found and < 3.00, mark as **FAIL**.
             - *Rule:* If NOT FOUND, mark as **PASS** but add a note "Not listed".
           - **Relevant Experience**: Calculate total years of experience relevant to this job.
             - *Rule:* If Actual Years < Required Years, mark as **FAIL**.
           - **Major**: Check semantic match (e.g., Informatics matches Computer Science).

        2. **SCORING RUBRIC (TOTAL 100%)**:
           
           **A. Relevansi Hard Skill & Pengalaman (Bobot 60%)**
           - Check if mandatory hard skills exist in the CV (Context matters!).
           - Score 0-60 based on how many required skills are present and relevant.
           
           **B. Senioritas & Konteks (Bobot 20%)**
           - Does the experience duration align with the role level?
           - Has the candidate handled projects of similar scale/complexity?
           - Score 0-20.

           **C. Kualitas Deskripsi & Dampak (Bobot 20%)**
           - **Action Verbs:** Does the CV use strong verbs (Led, Developed, Optimized) vs weak verbs (Helped, Responsible for)?
           - **Quantitative Impact:** Are there numbers/metrics (e.g., "Increased sales by 20%", "Managed 50 users")?
           - Score 0-20.

        === OUTPUT JSON FORMAT (Bahasa Indonesia for Advice) ===
        {{
            "candidate_summary": "Ringkasan 2 kalimat (Bahasa Indonesia).",
            "mandatory_checks": {{
                "gpa": {{ "value": "Angka atau 'Tidak Dicantumkan'", "status": "PASS/FAIL", "reason": "..." }},
                "major": {{ "value": "Nama Jurusan", "status": "PASS/FAIL", "reason": "..." }},
                "experience_years": {{ "value": "Angka Tahun", "status": "PASS/FAIL", "reason": "..." }},
                "education_level": {{ "value": "S1/S2/D3", "status": "PASS/FAIL", "reason": "..." }}
            }},
            "rubric_scores": {{
                "relevance_score": 0,
                "seniority_score": 0,
                "quality_score": 0
            }},
            "skills_analysis": [
                {{ 
                    "skill": "Skill Name", 
                    "level": "Expert/Intermediate/Beginner/Missing", 
                    "score": 10.0, 
                    "reason": "Bukti..." 
                }}
            ],
            "suggestion": "Saran perbaikan (khususnya jika IPK tidak ada atau deskripsi kurang angka)."
        }}
        """

        try:
            print(f"🤖 [GEMINI RUBRIC] Analyzing: {job_title}")
            model = genai.GenerativeModel(get_best_available_model())
            
            response = model.generate_content(
                prompt, 
                generation_config={"response_mime_type": "application/json", "temperature": 0.0}
            )
            result = json.loads(response.text)

            # --- PYTHON VALIDATION ---
            mandatory_data = result.get('mandatory_checks', {})
            rubric = result.get('rubric_scores', {})

            # 1. Hitung Skor Dasar dari Rubrik AI
            base_score = (
                rubric.get('relevance_score', 0) + 
                rubric.get('seniority_score', 0) + 
                rubric.get('quality_score', 0)
            )
            
            # Pastikan tidak lebih dari 100
            final_score = min(100, base_score)

            # 2. Cek Mandatory (Gerbang Logika)
            is_failed = False
            fail_reasons = []

            for key, check in mandatory_data.items():
                # Khusus GPA: Jika AI bilang PASS (karena tidak ketemu), kita terima saja.
                # AI sudah diinstruksikan di prompt: "If NOT FOUND, mark as PASS".
                if check.get('status') == 'FAIL':
                    is_failed = True
                    fail_reasons.append(f"{key}: {check.get('reason')}")

            if is_failed:
                # Jika gagal syarat wajib (misal belum lulus atau exp kurang),
                # Skor di-cap maksimal 25% (Merah)
                final_score = min(final_score, 25.0)
                print(f"⛔ Mandatory Check Failed: {fail_reasons}")
            
            # Bonus: Jika GPA tidak ada, tambahkan saran otomatis di suggestion (jika belum ada)
            gpa_val = mandatory_data.get('gpa', {}).get('value', '').lower()
            if 'tidak' in gpa_val or 'not' in gpa_val or gpa_val == '-':
                suggestion = result.get('suggestion', '')
                if 'IPK' not in suggestion:
                    result['suggestion'] = suggestion + " Catatan: Sebaiknya cantumkan nilai IPK Anda agar lebih informatif bagi rekruter."

            return {
                "lulus": final_score >= 60,
                "skor_akhir": round(final_score, 2),
                "ai_analysis": result,
                "job_info": {"title": job_title, "description": job_desc_text}
            }

        except Exception as e:
            print(f"❌ Gemini Error: {e}")
            return {"lulus": False, "skor_akhir": 0, "error": str(e), "job_info": {"title": job_title}}