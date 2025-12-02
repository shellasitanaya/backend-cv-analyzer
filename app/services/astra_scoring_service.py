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
    """Auto-detect model terbaik."""
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Prioritas: Model 2.0 -> 1.5
        priority_list = ['models/gemini-2.0-flash', 'models/gemini-1.5-pro', 'models/gemini-1.5-flash']
        for model_name in priority_list:
            if model_name in available_models: return model_name
        return available_models[0]
    except: return 'models/gemini-1.5-flash'

class AstraScoringService:
    """
    Service penilaian CV berbasis Rubrik 60/20/20.
    Fokus: Mengaudit kualitas penulisan dan bukti kompetensi.
    """

    @staticmethod
    def analyze_cv_with_gemini(cv_text: str, job_desc_text: str, job_title: str = "General Job") -> Dict:
        if not GENAI_API_KEY: return {"error": "API Key Error"}

        current_year = datetime.now().year

        # --- LOGGING ---
        print("\n" + "="*70)
        print(f"🚀 [ASTRA OPTIMIZER] ANALYZING: {job_title}")
        print("="*70)

        # --- PROMPT: RUBRIK 60/20/20 & EVIDENCE AUDIT ---
        prompt = f"""
        Act as a Senior CV Consultant & Optimizer.
        Your goal is to audit the QUALITY of the candidate's CV based on the Job Description.
        Do not guess their skill level. Judge how well they **DEMONSTRATE** it in the text.

        === JOB TARGET ===
        POSITION: {job_title}
        JD: "{job_desc_text}"
        CURRENT YEAR: {current_year}

        === CANDIDATE CV ===
        {cv_text[:30000]}

        === SCORING RUBRIC (TOTAL 100.0) ===
        
        1. **Relevansi Hard Skill (Bobot 60.0)**
           - Score based on the presence of required skills.
           - *Calculation:* If 10 skills needed and 8 are found (in any section), base score is high.
        
        2. **Senioritas & Durasi (Bobot 20.0)**
           - Check if total relevant experience meets the requirement.
           - Check if the role titles match the seniority level.

        3. **Kualitas Deskripsi & Dampak (Bobot 20.0)**
           - **Action Verbs:** Are they using "Led", "Developed", "Architected"? (Good) or "Helped", "Responsible for"? (Weak)
           - **Quantitative Impact:** Are there numbers? (e.g. "20% growth", "10k users").
           - *Penalty:* If description is generic/vague, score low here.

        === INSTRUCTIONS FOR SKILL ANALYSIS ===
        For each required skill, assign a **"Proof Level"** (not Skill Level):

        - **"Strong Evidence" (10)**: Appears in "Work Experience" WITH specific context/impact/metrics.
          *Feedback:* "Sangat baik. Bukti kuat dengan konteks nyata."
        
        - **"Standard Context" (7.5)**: Appears in "Work Experience" but generic description (no metrics).
          *Feedback:* "Ada di pengalaman kerja, tapi deskripsi terlalu umum. Tambahkan dampak/angka (Impact) agar lebih meyakinkan."
        
        - **"Listed Only" (5.0)**: Only found in "Skills" list or "Education" without project context.
          *Feedback:* "Hanya scannable sebagai kata kunci. Wajib masukkan ke deskripsi pengalaman kerja dengan contoh nyata."
        
        - **"Missing" (0.0)**: Not found.
          *Feedback:* "Fatal. Keyword ini tidak ditemukan. Tambahkan segera jika Anda memilikinya."

        === OUTPUT JSON FORMAT ===
        {{
            "candidate_summary": "Ringkasan audit CV 2 kalimat (Bahasa Indonesia).",
            "mandatory_checks": {{
                "gpa": {{ "value": "Angka/Not Listed", "status": "PASS/NOTE" }},
                "major": {{ "value": "Nama Jurusan", "status": "PASS/FAIL" }},
                "experience_years": {{ "value": "Angka", "status": "PASS/FAIL" }}
            }},
            "rubric_scores": {{
                "relevance_score": 0.0, 
                "seniority_score": 0.0, 
                "quality_score": 0.0
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

            # --- CALCULATION ---
            rubric = result.get('rubric_scores', {})
            
            # 1. Total Score (60+20+20)
            final_score = float(rubric.get('relevance_score', 0)) + \
                          float(rubric.get('seniority_score', 0)) + \
                          float(rubric.get('quality_score', 0))
            
            # Cap at 100
            final_score = min(100.0, final_score)

            # 2. Mandatory Penalty (Strict Filter)
            mandatory = result.get('mandatory_checks', {})
            is_failed = False
            fail_reasons = []
            
            # Cek Status (Kecuali GPA, GPA pass/note aman)
            if mandatory.get('major', {}).get('status') == 'FAIL':
                is_failed = True; fail_reasons.append("Jurusan Tidak Relevan")
            if mandatory.get('experience_years', {}).get('status') == 'FAIL':
                is_failed = True; fail_reasons.append("Pengalaman Kurang")

            if is_failed:
                final_score = min(final_score, 30.0) # Penalty keras
                print(f"⛔ GATEKEEPER: Failed due to {fail_reasons}")

            # --- LOGGING TO TERMINAL ---
            print(f"\n📊 RUBRIC SCORE:")
            print(f"   - Relevansi (60%): {rubric.get('relevance_score')}")
            print(f"   - Senioritas (20%): {rubric.get('seniority_score')}")
            print(f"   - Kualitas (20%): {rubric.get('quality_score')}")
            print(f"   🏁 TOTAL: {final_score:.2f}%")
            print("="*70 + "\n")

            return {
                "lulus": final_score >= 60,
                "skor_akhir": round(final_score, 2),
                "ai_analysis": result,
                "job_info": {"title": job_title, "description": job_desc_text}
            }

        except Exception as e:
            print(f"❌ Gemini Error: {e}")
            return {"lulus": False, "skor_akhir": 0, "error": str(e), "job_info": {"title": job_title}}