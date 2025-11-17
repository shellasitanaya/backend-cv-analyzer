from app.extensions import db
from app.models import Skill
import uuid

def seed():
    print("🌱 Seeding skills...")

    skills = [

        # Tech / Programming
        "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "PHP", "Swift", "Kotlin",
        "Rust", "Ruby", "Dart", "R", "MATLAB",

        # Frameworks & Libraries
        "React", "Vue.js", "Angular", "Svelte",
        "Node.js", "Express.js", "Next.js", "Nuxt.js",
        "Flask", "Django", "Laravel", "FastAPI", "Spring Boot",
        "Flutter", "React Native",

        # Web Tech
        "HTML", "CSS", "TailwindCSS", "Bootstrap",
        "REST API", "GraphQL", "WebSockets",

        # Databases
        "SQL", "NoSQL",
        "MySQL", "PostgreSQL", "SQLite", 
        "MongoDB", "Redis", "Elasticsearch", "MariaDB",

        # Tools & General Tech
        "Git", "GitHub", "GitLab", "Docker", "Kubernetes", "Linux",
        "Bash Scripting", "PowerShell",
        "Microservices", "System Design",

        # Data & Artificial Intelligence
        "Data Analysis", "Machine Learning", "Deep Learning",
        "Natural Language Processing", "Computer Vision",
        "TensorFlow", "PyTorch", "Scikit-learn", "Pandas", "NumPy",
        "Jupyter Notebook", "R Programming",
        "Data Visualization",
        "Power BI", "Tableau", "Looker Studio",
        "Big Data", "Hadoop", "Spark",
        "ETL", "Data Cleaning", "Feature Engineering",
        "Model Deployment", "MLOps",

        # Cloud & DevOps
        "AWS", "Azure", "Google Cloud Platform",
        "CI/CD", "Terraform", "Jenkins",
        "Ansible", "Prometheus", "Grafana",
        "NGINX", "Server Administration",

        # Cybersecurity
        "Network Security", "Penetration Testing",
        "Ethical Hacking", "OWASP", "Firewall Management",
        "Incident Response", "Cryptography",

        # UI/UX & Design
        "Figma", "Adobe XD", "Canva", "Photoshop", "Illustrator",
        "UI Design", "UX Research", "Wireframing", "Prototyping",
        "Design Thinking",

        # Business & Management Skills
        "Business Analysis", "Product Management",
        "Project Management", "Scrum", "Agile",
        "Requirement Gathering", "Data-Driven Decision Making",

        # Marketing & Communications
        "SEO", "SEM",
        "Digital Marketing", "Content Marketing",
        "Social Media Management",
        "Copywriting", "Brand Strategy",

        # Soft Skills
        "Communication", "Leadership", "Problem Solving",
        "Time Management", "Teamwork", "Critical Thinking",
        "Creativity", "Adaptability", "Negotiation",
        "Public Speaking", "Customer Service",
        "Decision Making", "Emotional Intelligence",

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

