from app.extensions import db
from app.models import Skill
import uuid

def seed():
    print("🌱 Seeding skills...")

    skills = [
        # Tech / Programming
        "Python", "JavaScript", "Java", "C++", "C#", "Go", "PHP", "Swift", "Kotlin",
        "HTML", "CSS", "SQL", "NoSQL", "React", "Vue.js", "Angular", "Node.js", "Flask", "Django", "Laravel",
        "FastAPI", "TensorFlow", "PyTorch", "Scikit-learn", "Pandas", "NumPy",
        "Git", "Docker", "Kubernetes", "Linux", "REST API", "GraphQL",

        # Data & AI
        "Data Analysis", "Machine Learning", "Deep Learning", "Data Visualization", "Power BI",
        "Tableau", "Big Data", "ETL", "Excel", "Data Cleaning",

        # Cloud / DevOps
        "AWS", "Azure", "Google Cloud", "CI/CD", "Terraform",

        # UI/UX & Design
        "Figma", "Adobe XD", "Canva", "UI Design", "UX Research",

        # Soft Skills
        "Communication", "Leadership", "Problem Solving", "Time Management", "Teamwork",
        "Critical Thinking", "Project Management", "Adaptability",

        # Extra
        "Public Speaking", "Negotiation", "Customer Service", "Content Writing",
        "Marketing", "Sales", "SEO", "Social Media Management"
    ]

    count = 0
    for skill_name in skills:
        existing = Skill.query.filter_by(skill_name=skill_name).first()
        if not existing:
            db.session.add(Skill(
                id=str(uuid.uuid4()),
                skill_name=skill_name
            ))
            count += 1

    db.session.commit()
    print(f"✅ Seeded {count} new skills successfully!")