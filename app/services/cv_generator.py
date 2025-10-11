import os
import json
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from app.models import Candidate
from flask import current_app
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")


def enhance_with_ai(candidate_data):
    """
    Gunakan OpenAI untuk memperhalus konten CV (summary, experience, skills, education)
    """
    skills = candidate_data.get("skills") or ", ".join(
        candidate_data.get("structured_profile_json", {}).get("hard_skills", [])
    )

    prompt = f"""
    Kamu adalah asisten profesional penulis CV.
    Tolong tulis ulang konten berikut agar lebih profesional, jelas, dan ATS-friendly.

    === Informasi Kandidat ===
    Nama: {candidate_data.get('extracted_name', '')}
    Summary: {candidate_data.get('summary', '')}
    Pengalaman: {candidate_data.get('experience', '')}
    Skill: {skills}
    Pendidikan: {candidate_data.get('education', '')}

    Format jawaban kamu seperti ini:
    {{
        "summary": "...",
        "experience": "...",
        "skills": "...",
        "education": "..."
    }}
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )

        text = response.choices[0].message.content.strip()
        try:
            improved = json.loads(text)
        except Exception:
            improved = {"summary": text, "experience": "", "skills": skills, "education": ""}

        candidate_data.update(improved)
        return candidate_data

    except Exception as e:
        print(f"⚠️ Error AI enhancement: {e}")
        return candidate_data


def build_cv(candidate_id):
    """
    Generate CV PDF berdasarkan template dan data dari Candidate
    """
    candidate = Candidate.query.filter_by(id=candidate_id).first()
    if not candidate:
        raise ValueError(f"Candidate with {candidate_id} ID not found")

    candidate_data = candidate.__dict__.copy()
    candidate_data.pop("_sa_instance_state", None)

    candidate_data = enhance_with_ai(candidate_data)

    template_dir = os.path.join(current_app.root_path, "template")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("ats-friendly.html")
    rendered_html = template.render(candidate=candidate_data)

    output_dir = os.path.join(current_app.root_path, "generated")
    os.makedirs(output_dir, exist_ok=True)

    safe_name = candidate_data.get("extracted_name", f"candidate_{candidate_id}")
    output_path = os.path.join(output_dir, f"{safe_name}_CV.pdf")

    HTML(string=rendered_html).write_pdf(output_path)

    print(f"✅ CV has successfully generated to {output_path}")
    return output_path
