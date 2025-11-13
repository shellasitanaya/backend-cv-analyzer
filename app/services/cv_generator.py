import os
import json
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from app.models import Candidate
from flask import current_app
import google.generativeai as genai

# Configure Gemini
def configure_gemini():
    """Configure Gemini API"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("⚠️ Gemini API key not found")
        return False
    
    try:
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        print(f"⚠️ Gemini configuration failed: {e}")
        return False

def enhance_with_gemini(candidate_data):
    """
    Gunakan Google Gemini untuk memperhalus konten CV dengan prompt yang aman
    """
    # Check if Gemini is configured
    if not configure_gemini():
        print("⚠️ Gemini not configured, skipping enhancement")
        return candidate_data

    try:
        # Use the most stable model - Gemini 2.5 Flash
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        
        # Prepare data - sanitize first
        skills = candidate_data.get("skills") or ", ".join(
            candidate_data.get("structured_profile_json", {}).get("hard_skills", [])
        )

        # Sanitize input data
        summary = str(candidate_data.get('summary', ''))[:500]  # Limit length
        experience = str(candidate_data.get('experience', ''))[:500]
        education = str(candidate_data.get('education', ''))[:500]

        # Create SAFE prompt - sangat spesifik dan profesional
        prompt = f"""
        TASK: Improve this CV content for professional use.

        ORIGINAL CONTENT:
        SUMMARY: {summary}
        EXPERIENCE: {experience}
        SKILLS: {skills}
        EDUCATION: {education}

        INSTRUCTIONS:
        1. Make the summary more professional (2-3 sentences max)
        2. Improve experience descriptions using action verbs
        3. Format skills clearly
        4. Keep education concise
        5. Use formal Indonesian language
        6. Focus on achievements and technical skills

        OUTPUT FORMAT (JSON only):
        {{
            "summary": "Improved professional summary here",
            "experience": "Improved experience description here",
            "skills": "Formatted skills here",
            "education": "Improved education description here"
        }}

        Return only the JSON object, no other text.
        """

        # Generate content with safety settings
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,  # Lower for more consistent results
                top_p=0.8,
                top_k=40,
                max_output_tokens=800,
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

        # Check response carefully
        if not response.parts:
            print(f"❌ Gemini response blocked. Finish reason: {response.candidates[0].finish_reason if response.candidates else 'Unknown'}")
            # Try fallback with simpler prompt
            return enhance_with_gemini_fallback(candidate_data)

        # Process response
        text = response.text.strip()
        print(f"🔍 Gemini raw response: {text}")

        # Clean response
        text = text.replace('```json', '').replace('```', '').strip()
        
        try:
            improved = json.loads(text)
            print("✅ Gemini enhancement successful")
            
            # Validate improved data
            if not improved.get('summary'):
                improved['summary'] = candidate_data.get('summary', '')
            if not improved.get('experience'):
                improved['experience'] = candidate_data.get('experience', '')
            if not improved.get('skills'):
                improved['skills'] = skills
            if not improved.get('education'):
                improved['education'] = candidate_data.get('education', '')
                
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON: {e}")
            print(f"Raw response: {text}")
            # Use fallback extraction
            improved = extract_key_value_from_text(text)
        
        # Update candidate data
        candidate_data.update(improved)
        return candidate_data

    except Exception as e:
        print(f"⚠️ Gemini enhancement error: {e}")
        # Fallback to rule-based
        return apply_advanced_rule_based_improvement(candidate_data)


def enhance_with_gemini_fallback(candidate_data):
    """
    Fallback dengan prompt yang lebih sederhana
    """
    try:
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        
        skills = candidate_data.get("skills") or ", ".join(
            candidate_data.get("structured_profile_json", {}).get("hard_skills", [])
        )

        # Very simple and safe prompt
        prompt = f"""Improve this CV text professionally:

"{candidate_data.get('summary', '')}"

Return only the improved version in Indonesian."""
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,
                max_output_tokens=200,
            )
        )

        if response.parts:
            improved_summary = response.text.strip()
            candidate_data["summary"] = improved_summary
            print("✅ Gemini fallback enhancement successful")
        
        return candidate_data
        
    except Exception as e:
        print(f"⚠️ Gemini fallback also failed: {e}")
        return apply_advanced_rule_based_improvement(candidate_data)
    
def apply_advanced_rule_based_improvement(candidate_data):
    """
    Advanced rule-based improvement untuk CV yang profesional
    """
    skills = candidate_data.get("skills") or ", ".join(
        candidate_data.get("structured_profile_json", {}).get("hard_skills", [])
    )
    
    # Professional templates untuk summary
    professional_templates = [
        "Mahasiswa Teknik Informatika yang berdedikasi dengan keahlian dalam {skills}. Berpengalaman dalam pengembangan software dan solusi teknologi inovatif.",
        "Calon lulusan Teknik Informatika dengan passion dalam {skills}. Memiliki kemampuan analitis yang kuat dan berpengalaman dalam project development.",
        "Professional dengan latar belakang Teknik Informatika dan pengalaman dalam {skills}. Berkomitmen untuk memberikan solusi teknologi yang efektif dan efisien."
    ]
    
    # Improve summary dengan template profesional
    original_summary = candidate_data.get('summary', '')
    
    # Clean up informal language
    informal_words = {
        'gacor': 'mahir',
        'ganteng': 'profesional', 
        'jago': 'ahli',
        'mantap': 'handal',
        'keren': 'impresif',
        'suka': 'memiliki minat dalam',
        'bisa': 'mampu',
        'ngoding': 'pemrograman',
        'coding': 'pemrograman',
        'tekun belajar': 'berdedikasi dalam pembelajaran',
        'mahir dalam berbagai hal berbau pemrograman': 'memiliki keahlian komprehensif dalam pemrograman',
        'mahir dalam mengelola': 'berpengalaman dalam pengembangan'
    }
    
    cleaned_summary = original_summary
    for informal, formal in informal_words.items():
        cleaned_summary = cleaned_summary.replace(informal, formal)
    
    # Create professional summary
    if cleaned_summary and len(cleaned_summary.strip()) > 20:  # Jika summary cukup panjang
        improved_summary = cleaned_summary
    else:
        # Gunakan template profesional
        import random
        template = random.choice(professional_templates)
        improved_summary = template.format(skills=skills)
    
    # Improve work experience descriptions
    work_experience = candidate_data.get('work_experience', [])
    improved_experience = []
    
    professional_verbs = [
        "Mengembangkan", "Mengelola", "Mengimplementasikan", "Merancang", 
        "Mengoptimalkan", "Menganalisis", "Memimpin", "Berkolaborasi"
    ]
    
    for exp in work_experience:
        if isinstance(exp, dict):
            description = exp.get('description', '')
            job_title = exp.get('job_title', '')
            
            # Clean informal language
            for informal, formal in informal_words.items():
                description = description.replace(informal, formal)
            
            # Improve description structure
            if description and len(description.strip()) > 0:
                # Jika deskripsi masih informal, buat yang lebih profesional
                if any(word in description.lower() for word in ['mahir', 'bisa', 'dapat']):
                    # Buat deskripsi profesional berdasarkan job title
                    if 'software' in job_title.lower() or 'engineer' in job_title.lower():
                        description = "• Mengembangkan dan memelihara aplikasi software menggunakan teknologi modern\n• Berkolaborasi dengan tim untuk merancang dan mengimplementasikan solusi teknis\n• Melakukan testing dan debugging untuk memastikan kualitas kode"
                    elif 'developer' in job_title.lower():
                        description = "• Mengembangkan aplikasi web dan mobile yang responsif\n• Mengimplementasikan fitur-fitur baru berdasarkan kebutuhan user\n• Mengoptimalkan performa dan keamanan aplikasi"
                    else:
                        description = "• Berkontribusi dalam pengembangan project teknologi\n• Berkolaborasi dengan tim cross-functional\n• Menerapkan best practices dalam pengembangan software"
                
                # Pastikan format bullet points
                if not any(marker in description for marker in ['•', '-', '*']):
                    lines = [line.strip() for line in description.split('.') if line.strip()]
                    description = '\n'.join([f"• {line}" for line in lines if line])
            
            improved_exp = exp.copy()
            improved_exp['description'] = description
            improved_experience.append(improved_exp)
        else:
            improved_experience.append(exp)
    
    # Improve skills formatting
    if skills and isinstance(skills, str):
        # Capitalize dan format skills
        skills_list = [skill.strip() for skill in skills.split(',')]
        improved_skills = ', '.join([skill.strip().title() for skill in skills_list])
        
        # Group similar skills
        tech_skills = []
        soft_skills = []
        
        for skill in skills_list:
            skill_lower = skill.lower()
            if any(tech in skill_lower for tech in ['python', 'javascript', 'java', 'react', 'flask', 'node', 'html', 'css', 'git', 'sql', 'database']):
                tech_skills.append(skill.strip().title())
            else:
                soft_skills.append(skill.strip().title())
        
        # Jika ada soft skills, format secara terpisah
        if soft_skills:
            improved_skills = f"{', '.join(tech_skills)} | {', '.join(soft_skills)}"
        else:
            improved_skills = ', '.join(tech_skills)
    else:
        improved_skills = skills
    
    # Improve education description
    education = candidate_data.get('education', [])
    improved_education = []
    
    for edu in education:
        if isinstance(edu, dict):
            improved_edu = edu.copy()
            improved_education.append(improved_edu)
        else:
            improved_education.append(edu)
    
    improved_data = {
        "summary": improved_summary,
        "work_experience": improved_experience,
        "skills": improved_skills,
        "education": improved_education
    }
    
    print("✅ Applied professional rule-based enhancement")
    
    # Update candidate data
    candidate_data.update(improved_data)
    return candidate_data
    
def extract_key_value_from_text(text):
    """
    Fallback method to extract key-value pairs from text response
    """
    improved = {
        "summary": "",
        "experience": "",
        "skills": "", 
        "education": ""
    }
    
    lines = text.split('\n')
    current_key = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check for key patterns
        if '"summary":' in line or 'summary:' in line:
            current_key = 'summary'
            value = line.split(':', 1)[1].strip().strip('",')
            improved['summary'] = value
        elif '"experience":' in line or 'experience:' in line:
            current_key = 'experience' 
            value = line.split(':', 1)[1].strip().strip('",')
            improved['experience'] = value
        elif '"skills":' in line or 'skills:' in line:
            current_key = 'skills'
            value = line.split(':', 1)[1].strip().strip('",')
            improved['skills'] = value
        elif '"education":' in line or 'education:' in line:
            current_key = 'education'
            value = line.split(':', 1)[1].strip().strip('",')
            improved['education'] = value
        elif current_key and line.startswith('"') and line.endswith('"'):
            # Continue multi-line values
            improved[current_key] += " " + line.strip('",')
    
    return improved

def enhance_cv_content(candidate_data):
    """
    Main enhancement function with fallback
    """
    # Try Gemini first
    enhanced_data = enhance_with_gemini(candidate_data.copy())
    
    # Check if enhancement actually happened
    original_summary = candidate_data.get('summary', '')
    enhanced_summary = enhanced_data.get('summary', '')
    
    if enhanced_summary and enhanced_summary != original_summary:
        print("✅ AI enhancement applied successfully")
        return enhanced_data
    else:
        print("⚠️ AI enhancement failed, using original data")
        return candidate_data
    
def build_cv(candidate_id):
    """
    Generate CV PDF berdasarkan data kandidat di database
    """
    candidate = Candidate.query.filter_by(id=candidate_id).first()
    if not candidate:
        raise ValueError(f"Candidate with ID {candidate_id} not found")

    candidate_data = candidate.__dict__.copy()
    candidate_data.pop("_sa_instance_state", None)

    # apa ini tlg dicek lg ya
    # candidate_data = enhance_with_ai(candidate_data)

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


def build_cv_from_data(data, template="modern"):
    """
    Generate CV directly from user form data (no DB).
    """
    try:
        print("🔍 [DEBUG] ========== RAW DATA RECEIVED ==========")
        print(json.dumps(data, indent=2, default=str))
        print("🔍 [DEBUG] =======================================")

        # Extract data - FIXED: use work_experience instead of experience
        name = data.get("extracted_name") or data.get("name") or ""
        email = data.get("email", "")
        phone = data.get("phone", "")
        summary = data.get("summary", "")
        experience_raw = data.get("work_experience") or data.get("experience") or []  # FIXED
        education_raw = data.get("education") or []
        skills_raw = data.get("skills", "")
        linkedin = data.get("linkedin_url", "") or data.get("linkedin", "")
        portfolio = data.get("portfolio_url", "")

        print(f"🔍 [DEBUG] work_experience data: {experience_raw}")
        print(f"🔍 [DEBUG] Type: {type(experience_raw)}")
        
        # Normalize work experience - FIXED VERSION
        work_experience = []
        if isinstance(experience_raw, list) and experience_raw:
            for i, exp in enumerate(experience_raw):
                print(f"🔍 [DEBUG] --- Processing Work Experience {i} ---")
                print(f"🔍 [DEBUG] Raw exp: {exp}")
                if isinstance(exp, dict):
                    print(f"🔍 [DEBUG] job_title: '{exp.get('job_title')}'")
                    print(f"🔍 [DEBUG] company_name: '{exp.get('company_name')}'")
                    
                    # Handle description
                    description = exp.get("description") or ""
                    if isinstance(description, str) and description.strip():
                        description_list = [line.strip() for line in description.split('\n') if line.strip()]
                        description_final = description_list if len(description_list) > 1 else description
                    else:
                        description_final = description
                    
                    # Get job title and company name
                    job_title = (exp.get("job_title") or "").strip()
                    company_name = (exp.get("company_name") or "").strip()
                    
                    cleaned_exp = {
                        "job_title": job_title,
                        "company_name": company_name,
                        "start_date": (exp.get("start_date") or "").strip(),
                        "end_date": (exp.get("end_date") or "").strip(),
                        "description": description_final
                    }
                    
                    print(f"✅ [DEBUG] Cleaned experience: {cleaned_exp}")
                    
                    # Always add if we have the data
                    work_experience.append(cleaned_exp)
        
        print(f"✅ [DEBUG] Final work_experience: {work_experience}")

        # Normalize education
        education_list = []
        if isinstance(education_raw, list) and education_raw:
            for i, edu in enumerate(education_raw):
                print(f"🔍 [DEBUG] --- Processing Education {i} ---")
                print(f"🔍 [DEBUG] Raw edu: {edu}")
                if isinstance(edu, dict):
                    cleaned_edu = {
                        "degree": (edu.get("degree") or "").strip(),
                        "university": (edu.get("university") or "").strip(),
                        "graduation_year": (edu.get("graduation_year") or "").strip(),
                        "major": (edu.get("major") or "").strip()
                    }
                    
                    print(f"✅ [DEBUG] Cleaned education: {cleaned_edu}")
                    education_list.append(cleaned_edu)

        print(f"✅ [DEBUG] Final education_list: {education_list}")

        # Normalize skills
        if isinstance(skills_raw, list):
            hard_skills_list = [s.strip() for s in skills_raw if s and str(s).strip()]
            skills_string = ", ".join(hard_skills_list)
        else:
            hard_skills_list = [s.strip() for s in (str(skills_raw) or "").split(",") if s.strip()]
            skills_string = ", ".join(hard_skills_list)

        # Build candidate data structure - FIXED STRUCTURE
        candidate_data = {
            "personal_info": {
                "full_name": name,
                "email": email,
                "phone_number": phone,
                "linkedin_url": linkedin,
                "portfolio_url": portfolio,
            },
            "summary": summary,
            "work_experience": work_experience,  # Use the correct key
            "education": education_list,
            "skills": {
                "hard_skills": hard_skills_list,
                "soft_skills": [],
            },
        }

        # Add flat keys for template compatibility - FIXED
        candidate_data.update({
            "extracted_name": name,
            "extracted_email": email,
            "extracted_phone": phone,
            "experience": work_experience,  # Keep for backward compatibility
            "education_text": education_list,
            "skills": skills_string,
            "structured_profile_json": {"hard_skills": hard_skills_list},
        })

        print(f"✅ [DEBUG] ========== FINAL CANDIDATE DATA ==========")
        print(f"✅ [DEBUG] Name: {candidate_data.get('extracted_name')}")
        print(f"✅ [DEBUG] Work Experience items: {len(candidate_data.get('work_experience', []))}")
        for i, exp in enumerate(candidate_data.get('work_experience', [])):
            print(f"✅ [DEBUG]   Item {i}:")
            print(f"✅ [DEBUG]     job_title: '{exp.get('job_title')}'")
            print(f"✅ [DEBUG]     company_name: '{exp.get('company_name')}'")
            print(f"✅ [DEBUG]     start_date: '{exp.get('start_date')}'")
            print(f"✅ [DEBUG]     end_date: '{exp.get('end_date')}'")
        print(f"✅ [DEBUG] =========================================")

        print("🔄 Attempting AI enhancement with Gemini...")
        candidate_data = enhance_cv_content(candidate_data)

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
    
def safe_enhance_with_gemini(candidate_data):
    """
    Safe wrapper with comprehensive error handling
    """
    max_retries = 2
    for attempt in range(max_retries):
        try:
            return enhance_with_gemini(candidate_data)
        except Exception as e:
            print(f"⚠️ Gemini attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                print("❌ All Gemini attempts failed")
                return candidate_data