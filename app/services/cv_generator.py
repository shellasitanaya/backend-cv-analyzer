import os
import json
import logging
import re
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from app.models import Candidate
from flask import current_app
import google.generativeai as genai

# Configure logging
logger = logging.getLogger(__name__)

class CVGeneratorWithAI:
    def __init__(self):
        # GANTI DENGAN GEMINI API KEY YANG VALID
        self.api_key = 'AIzaSyDetnJo_x25cWqw44DVTb0an0aCo-6V3Ss'
        self._ai_model = None
    
        print(f"🔍 [DEBUG] API Key: {self.api_key[:10]}...{self.api_key[-10:] if self.api_key else 'EMPTY'}")
        print(f"🔍 [DEBUG] API Key length: {len(self.api_key) if self.api_key else 0}")

    @property
    def ai_model(self):
        """Lazy initialization of AI model"""
        if self._ai_model is None:
            try:
                genai.configure(api_key=self.api_key)
                self._ai_model = genai.GenerativeModel('models/gemini-2.5-flash-lite')
                logger.info("✅ AI model initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize AI model: {e}")
                self._ai_model = None
        return self._ai_model
    
    def improve_text_with_ai(self, text: str, text_type: str = "general") -> str:
        """
        Improve CV text using AI with career-focused prompts and clean formatting
        """
        if not text or not text.strip() or self.ai_model is None:
            return text
        
        try:
            # Skip very short texts
            if len(text.strip()) < 10:
                return text
                
            # VERY SPECIFIC career-focused prompts with NO FORMATTING instructions
            prompts = {
                "summary": """
                You are a professional career coach. Improve this CV summary to be more professional and impactful.
                Focus on: clarity, achievements, quantifiable results, and professional tone.
                Add measurable impact based on typical project scopes (user volume, performance gains, efficiency metrics).
                Keep it concise (2-3 sentences maximum).
                IMPORTANT: Return only plain text without any formatting, asterisks, markdown, or special characters.
                
                ORIGINAL SUMMARY: {text}
                """,
                
                "job_description": """
                You are a professional resume writer. Rewrite this job description to be more achievement-oriented with quantifiable metrics.
                Use strong action verbs and focus on measurable accomplishments.
                Add realistic metrics based on similar project scopes: user volume (e.g., 10K+ users), performance gains (e.g., 40% faster), 
                delivery speed (e.g., 25% quicker), efficiency improvements (e.g., 30% more efficient), cost savings, error reduction, etc.
                Keep it concise and impactful with 2-3 bullet points worth of content.
                CRITICAL: Return plain text only - no asterisks, no bold, no markdown formatting of any kind.
                
                ORIGINAL JOB DESCRIPTION: {text}
                """,
                
                "achievement": """
                As a professional resume editor, improve this work achievement to be more impactful with quantifiable results.
                Start with strong action verbs and add realistic metrics based on typical project impact.
                Include measurable outcomes like: performance improvements (15-50%), user growth (1K-100K), efficiency gains (20-60%), 
                cost reductions (10-40%), error rate decreases, faster delivery times, etc.
                Keep it to one clear, metrics-driven sentence.
                ESSENTIAL: Plain text output only - no formatting symbols, asterisks, or special characters.
                
                ORIGINAL ACHIEVEMENT: {text}
                """,
                
                "general": """
                You are a professional CV editor. Improve this text to be more suitable for a professional curriculum vitae.
                Add quantifiable impact and measurable results based on realistic project scopes.
                Make it concise, professional, and impactful with specific metrics.
                Return only the improved version as plain text without any formatting.
                
                ORIGINAL TEXT: {text}
                """
            }
            
            prompt_template = prompts.get(text_type, prompts["general"])
            prompt = prompt_template.format(text=text)
            
            # More permissive safety settings for career content
            response = self.ai_model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2,  # Lower for more consistent results
                    max_output_tokens=500,
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
            
            # BETTER response handling
            if response.parts:
                improved_text = response.text.strip()
                
                # COMPREHENSIVE CLEANING OF MARKDOWN AND FORMATTING
                improved_text = self._clean_all_formatting(improved_text)
                
                if improved_text and len(improved_text) > len(text) / 2:  # Reasonable length check
                    logger.info(f"✅ AI improved {text_type}")
                    return improved_text
                else:
                    logger.warning(f"⚠️ AI returned short/empty response for {text_type}")
                    return text
            else:
                # Detailed error analysis
                if response.candidates:
                    finish_reason = response.candidates[0].finish_reason
                    logger.warning(f"⚠️ AI response blocked. Finish reason: {finish_reason}")
                    
                    # Try fallback with simpler prompt
                    return self._improve_text_fallback(text, text_type)
                else:
                    logger.warning("⚠️ No candidates in response")
                    return text
                
        except Exception as e:
            logger.error(f"❌ AI phrasing failed: {e}")
            return self._improve_text_fallback(text, text_type)

    def _clean_all_formatting(self, text: str) -> str:
        """
        Remove all markdown and formatting from AI response
        """
        if not text:
            return text
        
        # Remove markdown bold and italic
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        
        # Remove any remaining asterisks (standalone)
        text = re.sub(r'(?<!\w)\*(?!\w)', '', text)
        
        # Remove markdown headers
        text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
        
        # Remove code formatting
        text = re.sub(r'`(.*?)`', r'\1', text)
        
        # Remove links but keep text
        text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
        
        # Remove quote marks around the entire text
        text = re.sub(r'^["\']|["\']$', '', text)
        
        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text

    def _improve_text_fallback(self, text: str, text_type: str) -> str:
        """
        Fallback method with simpler, safer prompts and no formatting
        """
        try:
            # Very simple and safe prompts with explicit no-formatting
            simple_prompts = {
                "summary": "Improve this professional summary using plain text only (no formatting): {text}",
                "job_description": "Improve this job description using plain text only (no asterisks, no formatting): {text}",
                "achievement": "Improve this achievement using plain text only: {text}",
                "general": "Improve this CV text using plain text only: {text}"
            }
            
            prompt = simple_prompts.get(text_type, simple_prompts["general"]).format(text=text)
            
            response = self.ai_model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=300,
                )
            )
            
            if response.parts:
                cleaned_text = self._clean_all_formatting(response.text.strip())
                return cleaned_text
            else:
                return text
                
        except Exception as e:
            logger.error(f"❌ Fallback also failed: {e}")
            return text
    
    def improve_bullet_points(self, points: list) -> list:
        """Improve a list of bullet points"""
        if not points or self.ai_model is None:
            return points
        
        improved_points = []
        for point in points:
            if point and point.strip():
                improved_point = self.improve_text_with_ai(point.strip(), "achievement")
                improved_points.append(improved_point)
            else:
                improved_points.append(point)
        return improved_points
    
    def apply_ai_phrasing(self, cv_data: dict) -> dict:
        """
        Apply AI phrasing with retry logic
        """
        if self.ai_model is None:
            logger.warning("⚠️ AI model not available")
            return cv_data
        
        improved_data = cv_data.copy()
        
        print("🔄 Applying AI phrasing with retry logic...")
        
        # Track improvements
        improvements_applied = 0
        
        # Improve summary with retry
        if improved_data.get('summary'):
            if isinstance(improved_data['summary'], str) and len(improved_data['summary'].strip()) > 15:
                original = improved_data['summary']
                improved = self._improve_with_retry(original, "summary")
                if improved != original:
                    improved_data['summary'] = improved
                    improvements_applied += 1
                    print(f"✅ Improved summary")
        
        # Improve work experiences (limit to 2)
        if improved_data.get('work_experience'):
            for i, exp in enumerate(improved_data['work_experience'][:2]):  # Limit to first 2
                if exp.get('description') and isinstance(exp['description'], str):
                    original = exp['description']
                    if len(original.strip()) > 20:
                        improved = self._improve_with_retry(original, "job_description")
                        if improved != original:
                            exp['description'] = improved
                            improvements_applied += 1
                            print(f"✅ Improved experience {i+1}")
        
        print(f"🎯 AI phrasing completed: {improvements_applied} improvements")
        return improved_data

    def _improve_with_retry(self, text: str, text_type: str, max_retries: int = 2) -> str:
        """
        Retry mechanism for AI improvements
        """
        for attempt in range(max_retries):
            try:
                improved = self.improve_text_with_ai(text, text_type)
                if improved != text and len(improved) > 10:
                    return improved
            except Exception as e:
                logger.warning(f"⚠️ Attempt {attempt + 1} failed: {e}")
        
        return text  # Return original if all retries fail
    
# Global instance
ai_cv_generator = CVGeneratorWithAI()

def build_cv(candidate_id):
    """
    Generate CV PDF berdasarkan data kandidat di database
    """
    candidate = Candidate.query.filter_by(id=candidate_id).first()
    if not candidate:
        raise ValueError(f"Candidate with ID {candidate_id} not found")

    candidate_data = candidate.__dict__.copy()
    candidate_data.pop("_sa_instance_state", None)

    template_dir = os.path.join(current_app.root_path, "template")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("ats-friendly.html")
    rendered_html = template.render(candidate=candidate_data)

    output_dir = os.path.join(current_app.root_path, "generated")
    os.makedirs(output_dir, exist_ok=True)

    safe_name = candidate_data.get("extracted_name", f"candidate_{candidate_id}")
    output_path = os.path.join(output_dir, f"{safe_name}_CV.pdf")

    HTML(string=rendered_html).write_pdf(output_path)

    print(f"✅ CV successfully generated: {output_path}")
    return output_path

def build_cv_from_data(data, template="modern", use_ai_phrasing=True):
    """
    Generate CV directly from user form data (no DB).
    """
    try:
        print("🔍 [DEBUG] ========== RAW DATA RECEIVED ==========")
        print(json.dumps(data, indent=2, default=str))
        print("🔍 [DEBUG] =======================================")

        # Extract data
        name = data.get("extracted_name") or data.get("name") or ""
        email = data.get("email", "")
        phone = data.get("phone", "")
        summary = data.get("summary", "")
        experience_raw = data.get("work_experience") or data.get("experience") or []
        education_raw = data.get("education") or []
        skills_raw = data.get("skills", "")
        linkedin = data.get("linkedin_url", "") or data.get("linkedin", "")
        portfolio = data.get("portfolio_url", "")

        print(f"🔍 [DEBUG] work_experience data: {experience_raw}")
        
        # Normalize work experience
        work_experience = []
        if isinstance(experience_raw, list) and experience_raw:
            for i, exp in enumerate(experience_raw):
                print(f"🔍 [DEBUG] --- Processing Work Experience {i} ---")
                if isinstance(exp, dict):
                    # Handle description
                    description = exp.get("description") or ""
                    if isinstance(description, str) and description.strip():
                        description_list = [line.strip() for line in description.split('\n') if line.strip()]
                        description_final = description_list if len(description_list) > 1 else description
                    else:
                        description_final = description
                    
                    cleaned_exp = {
                        "job_title": (exp.get("job_title") or "").strip(),
                        "company_name": (exp.get("company_name") or "").strip(),
                        "start_date": (exp.get("start_date") or "").strip(),
                        "end_date": (exp.get("end_date") or "").strip(),
                        "description": description_final
                    }
                    
                    work_experience.append(cleaned_exp)
        
        print(f"✅ [DEBUG] Final work_experience: {work_experience}")

        # Normalize education
        education_list = []
        if isinstance(education_raw, list) and education_raw:
            for edu in education_raw:
                if isinstance(edu, dict):
                    cleaned_edu = {
                        "degree": (edu.get("degree") or "").strip(),
                        "university": (edu.get("university") or "").strip(),
                        "graduation_year": (edu.get("graduation_year") or "").strip(),
                        "major": (edu.get("major") or "").strip()
                    }
                    education_list.append(cleaned_edu)

        print(f"✅ [DEBUG] Final education_list: {education_list}")

        # Normalize skills
        if isinstance(skills_raw, list):
            hard_skills_list = [s.strip() for s in skills_raw if s and str(s).strip()]
            skills_string = ", ".join(hard_skills_list)
        else:
            hard_skills_list = [s.strip() for s in (str(skills_raw) or "").split(",") if s.strip()]
            skills_string = ", ".join(hard_skills_list)

        # Build candidate data structure
        candidate_data = {
            "personal_info": {
                "full_name": name,
                "email": email,
                "phone_number": phone,
                "linkedin_url": linkedin,
                "portfolio_url": portfolio,
            },
            "summary": summary,
            "work_experience": work_experience,
            "education": education_list,
            "skills": {
                "hard_skills": hard_skills_list,
                "soft_skills": [],
            },
        }

        # Add flat keys for template compatibility
        candidate_data.update({
            "extracted_name": name,
            "extracted_email": email,
            "extracted_phone": phone,
            "experience": work_experience,
            "education_text": education_list,
            "skills": skills_string,
            "structured_profile_json": {"hard_skills": hard_skills_list},
        })

        print(f"✅ [DEBUG] Name: {candidate_data.get('extracted_name')}")
        print(f"✅ [DEBUG] Work Experience items: {len(candidate_data.get('work_experience', []))}")

        # Apply AI phrasing if enabled
        if use_ai_phrasing:
            print("🔄 Applying AI phrasing improvements...")
            candidate_data = ai_cv_generator.apply_ai_phrasing(candidate_data)
        else:
            print("ℹ️ AI phrasing disabled, using original content")

        # Render template
        template_dir = os.path.join(current_app.root_path, "templates")
        env = Environment(loader=FileSystemLoader(template_dir))
        
        try:
            template_file = env.get_template(f"{template}.html")
            print(f"✅ [DEBUG] Using template: {template}.html")
        except Exception as e:
            print(f"⚠️ [DEBUG] Template {template}.html not found, using fallback: {e}")
            template_file = env.get_template("ats-friendly.html")

        # Render with candidate data
        rendered_html = template_file.render(candidate=candidate_data)
        print("✅ [DEBUG] Template rendered successfully")

        # Save PDF
        output_dir = os.path.join(current_app.root_path, "generated", "temp")
        os.makedirs(output_dir, exist_ok=True)
        safe_name = "".join(c for c in (name or "User") if c.isalnum() or c in (" ", "-", "_")).strip().replace(" ", "_")
        output_path = os.path.join(output_dir, f"preview_{safe_name}.pdf")
        
        HTML(string=rendered_html).write_pdf(output_path)
        print(f"✅ [DEBUG] PDF generated at: {output_path}")

        return output_path

    except Exception as e:
        print(f"❌ [DEBUG] Error in build_cv_from_data: {e}")
        import traceback
        traceback.print_exc()
        raise e