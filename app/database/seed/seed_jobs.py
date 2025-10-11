from app.extensions import db
from app.models import Job, User
from datetime import datetime

def seed():
    print("🌱 Seeding jobs...")

    hr_id = User.query.filter_by(role='hr').first().id
    jobs = [
        Job(
            hr_user_id=hr_id,
            job_title="Backend Developer (Python)",
            job_location="Jakarta, Indonesia",
            job_description=(
                "Looking for a backend developer proficient in Python and Flask. "
                "You will work with REST APIs, databases, and cloud integration."
            ),
            min_gpa=3.00, 
            min_experience=2,
            max_experience=5,
            degree_requirements="Bachelor's in Computer Science",
            requirements_json=[
                "Experience with Flask or Django",
                "Understanding of REST API design"
            ],
            skills_json={
                "hard_skills": ["Python", "Flask", "PostgreSQL", "Docker"],
                "soft_skills": ["Communication", "Teamwork"],
                "optional_skills": ["AWS", "Redis"]
            },
            additional_info_json={
                "team": "Platform Engineering",
                "report_to": "Head of Engineering"
            },
            created_at=datetime.utcnow(),
        ),
        Job(
            hr_user_id=hr_id,
            job_title="Frontend Developer (React)",
            job_location="Bandung, Indonesia (Hybrid)",
            job_description=(
                "Join our frontend team to build interactive web apps using React and Tailwind CSS. "
                "Work closely with the backend and design teams to deliver high-quality UIs."
            ),
            min_gpa=3.87, 
            min_experience=1,
            max_experience=4,
            degree_requirements="Bachelor's in Information Technology",
            requirements_json=[
                "Proficiency in React",
                "Experience with version control (Git)"
            ],
            skills_json={
                "hard_skills": ["React", "JavaScript", "Tailwind CSS"],
                "soft_skills": ["Creativity", "Attention to detail"],
                "optional_skills": ["Next.js", "Figma"]
            },
            additional_info_json={
                "team": "Frontend Squad",
                "report_to": "UI Lead"
            },
            created_at=datetime.utcnow(),
        ),
    ]
    
    for job in jobs:
        existing_job = Job.query.filter_by(job_title=job.job_title).first()
        if existing_job:
            print(f"⚠️ Job '{job.job_title}' already exists. Skipping insert.")
            continue
        db.session.add(job)

    # db.session.bulk_save_objects(jobs)
    db.session.commit()
    print("✅ Jobs seeded successfully!")
