# cv_generator.py - VERSI DIPERBAIKI (PROPER BULLET FORMATTING & CLEAN AI PHRASING)
import os
import json
import logging
import re
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from app.models import Candidate
from flask import current_app
import google.generativeai as genai
from markupsafe import Markup  # PENTING: Untuk merender HTML di PDF

# Configure logging
logger = logging.getLogger(__name__)

class CVGeneratorWithAI:
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        self._ai_model = None
    
        print(f"🔍 [DEBUG] API Key from env: {'✅ Found' if self.api_key else '❌ Not found'}")
        if self.api_key:
            print(f"🔍 [DEBUG] API Key length: {len(self.api_key)}")

    @property
    def ai_model(self):
        """Lazy initialization of AI model"""
        if self._ai_model is None:
            try:
                if not self.api_key:
                    logger.warning("⚠️ No API key available")
                    return None
                    
                genai.configure(api_key=self.api_key)
                self._ai_model = genai.GenerativeModel('models/gemini-2.5-flash-lite')
                logger.info("✅ AI model initialized successfully")
                print("✅ AI model initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize AI model: {e}")
                print(f"❌ Failed to initialize AI model: {e}")
                self._ai_model = None
        return self._ai_model
    
    def improve_text_with_ai(self, text: str, text_type: str = "general", context: dict = None) -> str:
        """
        Improve CV text using AI with career-focused prompts
        """
        if not text or not text.strip() or self.ai_model is None:
            return text
        
        try:
            # Clean text sebelum dikirim ke AI
            text = self._clean_input_text(text)
            
            # Skip very short texts
            if len(text.strip()) < 10:
                return text
                
            # Context-aware prompts
            name = context.get('name', 'Candidate') if context else 'Candidate'
            job_title = context.get('job_title', '') if context else ''
            company = context.get('company', '') if context else ''
            
            prompts = {
                "summary": f"""
                You are a professional career coach specializing in resume writing.
                
                TASK: Improve this CV summary to be professional, impactful and concise.
                
                ORIGINAL SUMMARY: {text}
                
                IMPORTANT FORMATTING REQUIREMENTS:
                1. MUST use bullet points with '•' symbol
                2. Each bullet point MUST be on its own line
                3. Each sentence should be a separate bullet point
                4. No paragraphs, only bullet points
                5. Start each bullet with '• ' (bullet symbol + space)
                
                IMPROVEMENT GUIDELINES:
                1. Start with a strong opening statement
                2. Highlight key expertise and experience
                3. Add realistic achievements (use metrics like: 20% improvement, 30% increase, etc.)
                4. Limit to 4-5 bullet points maximum
                5. Make it ATS-friendly with relevant keywords
                6. Focus on value proposition
                
                OUTPUT FORMAT EXAMPLE:
                • Results-oriented software engineer with 5+ years experience
                • Specialized in Python, Flask and scalable web applications
                • Improved system performance by 20% and user engagement by 15%
                • Seeking to leverage technical expertise in managerial role
                
                NAME CONTEXT: {name}
                
                IMPROVED SUMMARY (ONLY BULLET POINTS, ONE PER LINE):
                """,
                
                "job_description": f"""
                You are a professional resume writer.
                
                TASK: Rewrite this job description to focus on achievements with quantifiable results.
                
                ORIGINAL DESCRIPTION: {text}
                
                IMPORTANT FORMATTING REQUIREMENTS:
                1. MUST use bullet points with '•' symbol
                2. Each bullet point MUST be on its own line
                3. Each achievement should be a separate bullet point
                4. No paragraphs, only bullet points
                5. Start each bullet with '• ' (bullet symbol + space)
                
                IMPROVEMENT GUIDELINES:
                1. Convert responsibilities into achievements
                2. Start each bullet with strong action verbs (Developed, Implemented, Led, etc.)
                3. Add realistic metrics (15-40% improvements, specific numbers)
                4. Focus on outcomes, not just duties
                5. Structure as clear bullet points
                
                OUTPUT FORMAT EXAMPLE:
                • Developed and deployed Python/Flask applications serving 10K+ users
                • Improved data processing speed by 40% through optimization
                • Collaborated with cross-functional teams to deliver projects 25% ahead of schedule
                • Reduced critical errors by 15% through strategic improvements
                
                JOB CONTEXT: {job_title} at {company}
                
                IMPROVED JOB DESCRIPTION (ONLY BULLET POINTS, ONE PER LINE):
                """,
                
                "general": f"""
                You are a professional CV editor.
                
                TASK: Improve this text for a professional curriculum vitae.
                
                ORIGINAL TEXT: {text}
                
                FORMATTING REQUIREMENTS:
                1. Use bullet points with '•' symbol
                2. Each bullet point on its own line
                3. No paragraphs or long blocks of text
                
                IMPROVEMENT GUIDELINES:
                1. Make it professional and concise
                2. Add quantifiable impact where appropriate
                3. Use industry-appropriate language
                4. Ensure clarity and readability
                
                IMPROVED TEXT (BULLET POINT FORMAT):
                """
            }
            
            prompt_template = prompts.get(text_type, prompts["general"])
            
            response = self.ai_model.generate_content(
                prompt_template,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=800,
                    top_p=0.9,
                ),
                safety_settings=[
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH", 
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    }
                ]
            )
            
            if response.parts:
                improved_text = response.text.strip()
                
                # Clean output - ENSURE PROPER BULLET FORMATTING
                improved_text = self._clean_and_format_bullet_points(improved_text, text_type)
                
                if improved_text and len(improved_text) > len(text) / 3:  # Reasonable length check
                    logger.info(f"✅ AI improved {text_type}")
                    return improved_text
                else:
                    logger.warning(f"⚠️ AI returned short/empty response for {text_type}")
                    return self._ensure_bullet_formatting(text)
            else:
                logger.warning(f"⚠️ No response parts for {text_type}")
                return self._ensure_bullet_formatting(text)
                
        except Exception as e:
            logger.error(f"❌ AI phrasing failed: {e}")
            return self._ensure_bullet_formatting(text)

    def _clean_input_text(self, text: str) -> str:
        """Clean input text before sending to AI"""
        if not text:
            return ""
        
        # Remove placeholder text and ellipsis
        text = re.sub(r'\b(adasasds|ddassd|\.\.\.)\b', '', text, flags=re.IGNORECASE)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()

    def _clean_and_format_bullet_points(self, text: str, text_type: str) -> str:
        """Clean AI output and ensure proper bullet point formatting"""
        if not text:
            return ""
        
        # Remove all markdown formatting except bullet points
        text = re.sub(r'[#`*]', '', text)
        
        # Remove quotes
        text = re.sub(r'^["\']|["\']$', '', text)
        
        # Remove ellipsis and placeholder text
        text = re.sub(r'\.\.\.', '.', text)
        text = re.sub(r'\b(adasasds|ddassd)\b', '', text, flags=re.IGNORECASE)
        
        # Split into lines
        lines = text.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Ensure bullet point formatting
            if not line.startswith('•'):
                # If line starts with dash or asterisk, convert to bullet
                if line.startswith('-') or line.startswith('*'):
                    line = '•' + line[1:]
                else:
                    line = '• ' + line
            
            # Ensure proper spacing after bullet
            if line.startswith('•') and len(line) > 1 and line[1] != ' ':
                line = '• ' + line[2:] if len(line) > 2 else line
            
            # Split long lines with multiple sentences into separate bullets
            sentences = re.split(r'(?<=[.!?])\s+', line)
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence:
                    # Ensure each sentence starts with bullet
                    if not sentence.startswith('•'):
                        sentence = '• ' + sentence
                    formatted_lines.append(sentence)
        
        # Join with newlines
        result = '\n'.join(formatted_lines)
        
        # Remove duplicate bullets
        result = re.sub(r'\n•+\s*', '\n• ', result)
        
        return result.strip()

    def _ensure_bullet_formatting(self, text: str) -> str:
        """Ensure any text has proper bullet point formatting"""
        if not text:
            return ""
        
        # Split into sentences and add bullet points
        sentences = re.split(r'(?<=[.!?])\s+', text)
        formatted_lines = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                # Clean up the sentence
                sentence = re.sub(r'^[•\-*]\s*', '', sentence)  # Remove existing bullets
                formatted_lines.append(f"• {sentence}")
        
        return '\n'.join(formatted_lines)
    
    def _convert_to_html_list(self, text: str) -> Markup:
        """
        [BARU] Mengubah teks dengan \n menjadi format HTML <ul><li> 
        agar rapi saat di-generate ke PDF.
        """
        if not text: return Markup("")
        
        lines = text.split('\n')
        list_items = ""
        
        for line in lines:
            clean_line = line.strip()
            if not clean_line: continue
            
            # Hapus simbol bullet point manual karena kita akan pakai tag <li>
            clean_line = re.sub(r'^[•\-*]\s*', '', clean_line)
            
            if clean_line:
                list_items += f'<li style="margin-bottom: 4px;">{clean_line}</li>'
        
        if not list_items: return Markup("")
        
        # Kembalikan sebagai Markup agar Jinja merender HTML-nya, bukan teksnya
        return Markup(f'<ul style="margin-left: 15px; padding-left: 0; list-style-type: disc;">{list_items}</ul>')
    
    def apply_ai_phrasing(self, cv_data: dict) -> dict:
        """
        Apply AI phrasing with proper context
        """
        if self.ai_model is None:
            logger.warning("⚠️ AI model not available")
            return cv_data
        
        improved_data = cv_data.copy()
        
        print("🔄 Applying AI phrasing...")
        
        # Get name for context
        name = improved_data.get('extracted_name') or improved_data.get('name', 'Candidate')
        
        # Improve summary - FORCE BULLET POINT FORMAT
        if improved_data.get('summary'):
            if isinstance(improved_data['summary'], str):
                context = {'name': name}
                improved_summary = self.improve_text_with_ai(
                    improved_data['summary'], 
                    "summary", 
                    context
                )
                if improved_summary:
                    improved_data['summary'] = improved_summary
                    print(f"✅ Improved summary with bullet points")
        
        # Improve work experiences - FORCE BULLET POINT FORMAT
        if improved_data.get('work_experience'):
            for i, exp in enumerate(improved_data['work_experience'][:3]):  # Limit to first 3
                if exp.get('description') and isinstance(exp['description'], str):
                    context = {
                        'name': name,
                        'job_title': exp.get('job_title', ''),
                        'company': exp.get('company_name', '')
                    }
                    improved_desc = self.improve_text_with_ai(
                        exp['description'],
                        "job_description",
                        context
                    )
                    if improved_desc:
                        exp['description'] = improved_desc
                        print(f"✅ Improved experience {i+1} with bullet points")
        
        return improved_data

# Global instance
ai_cv_generator = CVGeneratorWithAI()

def format_gpa_string(value, max_value="4.00"):
    """
    [BARU] Helper untuk memformat GPA menjadi 2 desimal
    Contoh: "4" -> "4.00", "3.5" -> "3.50"
    """
    try:
        # Bersihkan input
        val_str = str(value).strip().replace(',', '.')
        max_str = str(max_value).strip().replace(',', '.')
        
        if not val_str: return ""
        
        # Konversi ke float
        val_float = float(val_str)
        max_float = float(max_str)
        
        # Format ke 2 desimal
        return f"{val_float:.2f} / {max_float:.2f}"
    except ValueError:
        # Jika gagal konversi (misal ada teks), kembalikan aslinya
        return f"{value} / {max_value}"

# Add this function to cv_generator.py (at the bottom of the file)
def build_cv(candidate_id):
    """
    Build CV from database candidate data
    """
    from app.models import Candidate
    from flask import current_app
    
    try:
        print(f"🔍 [DEBUG] Building CV for candidate ID: {candidate_id}")
        
        # Fetch candidate from database
        candidate = Candidate.query.get(candidate_id)
        if not candidate:
            raise ValueError(f"Candidate with ID {candidate_id} not found")
        
        # Convert candidate to data dict
        candidate_data = {
            "name": candidate.full_name or "",
            "email": candidate.email or "",
            "phone": candidate.phone_number or "",
            "linkedin": candidate.linkedin_url or "",
            "portfolio": candidate.portfolio_url or "",
            "summary": candidate.summary or "",
            "work_experience": [],
            "education": [],
            "skills": []
        }
        
        # Add work experience if available
        if hasattr(candidate, 'experiences') and candidate.experiences:
            for exp in candidate.experiences:
                candidate_data["work_experience"].append({
                    "job_title": exp.job_title or "",
                    "company_name": exp.company_name or "",
                    "start_date": str(exp.start_date) if exp.start_date else "",
                    "end_date": str(exp.end_date) if exp.end_date else "Present",
                    "description": exp.description or ""
                })
        
        # Add education if available
        if hasattr(candidate, 'educations') and candidate.educations:
            for edu in candidate.educations:
                candidate_data["education"].append({
                    "degree": edu.degree or "",
                    "university": edu.university or "",
                    "graduation_year": str(edu.graduation_year) if edu.graduation_year else "",
                    "major": edu.major or "",
                    "gpa": str(edu.gpa) if edu.gpa else ""
                })
        
        # Add skills if available
        if hasattr(candidate, 'skills') and candidate.skills:
            for skill in candidate.skills:
                candidate_data["skills"].append({
                    "name": skill.name or "",
                    "elaboration": skill.elaboration or ""
                })
        
        # Use the existing build_cv_from_data function
        output_path, _ = build_cv_from_data(
            candidate_data, 
            template="ats-friendly",
            use_ai_phrasing=False  # Don't use AI for database-generated CVs
        )
        
        return output_path
        
    except Exception as e:
        print(f"❌ [ERROR] Failed to build CV from database: {e}")
        import traceback
        traceback.print_exc()
        raise e

def build_cv_from_data(data, template="modern", use_ai_phrasing=True):
    try:
        print("🔍 [DEBUG] Processing CV Data for PDF...")

        # 1. Extract Basic Data
        # Menggunakan logika fallback untuk nama
        name = data.get("extracted_name") or data.get("name") or data.get("personal_info", {}).get("full_name", "") or ""
        email = data.get("email", "")
        phone = data.get("phone", "")
        linkedin = data.get("linkedin_url") or data.get("linkedin", "")
        portfolio = data.get("portfolio_url") or data.get("portfolio", "")
        
        summary_text = data.get("summary", "")
        
        # 2. Normalize Experience
        experience_raw = data.get("work_experience") or data.get("experience") or []
        work_experience = []
        
        if isinstance(experience_raw, list):
            for exp in experience_raw:
                description = str(exp.get("description") or "").strip()
                
                # Pastikan format teks bullet (pakai \n dulu)
                if description:
                    description = ai_cv_generator._ensure_bullet_formatting(description)
                
                cleaned_exp = {
                    "job_title": str(exp.get("job_title") or "").strip(),
                    "company_name": str(exp.get("company_name") or "").strip(),
                    "start_date": str(exp.get("start_date") or "").strip(),
                    "end_date": str(exp.get("end_date") or "").strip(),
                    "description": description # Masih teks biasa
                }
                work_experience.append(cleaned_exp)

        # 3. Normalize Education dengan [PERBAIKAN GPA]
        education_raw = data.get("education") or []
        education_list = []
        if isinstance(education_raw, list):
            for edu in education_raw:
                gpa_val = str(edu.get("gpa") or "").strip()
                gpa_max = str(edu.get("gpa_max") or "4.00").strip()
                
                final_gpa = format_gpa_string(gpa_val, gpa_max)

                cleaned_edu = {
                    "degree": str(edu.get("degree") or "").strip(),
                    "university": str(edu.get("university") or "").strip(),
                    "graduation_year": str(edu.get("graduation_year") or "").strip(),
                    "major": str(edu.get("major") or "").strip(),
                    "gpa": final_gpa, # Sudah diformat
                    "gpa_raw": gpa_val,
                    "gpa_max_raw": gpa_max
                }
                education_list.append(cleaned_edu)

        # 4. Normalize Skills
        skills_raw = data.get("skills") or []
        formatted_skills = []
        if isinstance(skills_raw, list):
            for item in skills_raw:
                name_skill = str(item.get("name", "")).strip()
                if name_skill:
                    formatted_skills.append({
                        "name": name_skill,
                        "year": str(item.get("year", "")).strip(),
                        "elaboration": str(item.get("elaboration", "")).strip()
                    })

        # 5. Ensure summary bullet text
        if summary_text:
            summary_text = ai_cv_generator._ensure_bullet_formatting(summary_text)


        # 7. KONVERSI KE HTML LIST UNTUK PDF
        final_summary_html = ai_cv_generator._convert_to_html_list(summary_text)
        
        final_experience_html = []
        for exp in work_experience:
            new_exp = exp.copy()
            # Ubah description menjadi HTML Markup (ul/li)
            new_exp['description'] = ai_cv_generator._convert_to_html_list(exp['description'])
            final_experience_html.append(new_exp)

        # 8. Siapkan Data Akhir untuk Template
        # [PERBAIKAN KRITIS]: Memastikan semua data yang hilang (experience details, skills) 
        # masuk ke template dengan key yang diharapkan.
        final_data = {
            "full_name": name,
            "name": name,
            "extracted_name": name,
            "email": email,
            "phone": phone,
            "linkedin": linkedin,
            "portfolio": portfolio,
            
            # Summary (HTML LIST)
            "summary": final_summary_html,      
            
            # Experience (HTML LIST)
            "experience": final_experience_html, 
            "work_experience": final_experience_html, # Key Redundan untuk kompatibilitas
            
            # Education (GPA sudah diformat)
            "education": education_list,        
            
            # Skills
            "skills": formatted_skills,
            "skills_list": formatted_skills, # Key Redundan untuk kompatibilitas
            "skills_string": ", ".join([s["name"] for s in formatted_skills if s["name"]]), # Untuk template yang hanya butuh string
            
            "personal_info": { # Support legacy templates access
                "full_name": name,
                "name": name,
                "email": email,
                "phone_number": phone,
                "linkedin_url": linkedin,
                "portfolio_url": portfolio
            }
        }

        # 9. Render Template
        # ... (Kode Render Template tidak diubah)
        template_dir = os.path.join(current_app.root_path, "templates")
        env = Environment(loader=FileSystemLoader(template_dir))
        
        try:
            template_file = env.get_template(f"{template}.html")
        except:
            template_file = env.get_template("ats-friendly.html")

        rendered_html = template_file.render(candidate=final_data)

        # Generate PDF Path
        output_dir = os.path.join(current_app.root_path, "generated", "temp")
        os.makedirs(output_dir, exist_ok=True)
        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', name) or "user"
        output_path = os.path.join(output_dir, f"cv_{safe_name}_{template}.pdf")
        
        # Write PDF
        HTML(string=rendered_html).write_pdf(output_path)
        
        return output_path, final_data

    except Exception as e:
        print(f"❌ [CRITICAL ERROR] Build CV Failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise e