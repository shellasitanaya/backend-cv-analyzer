from app.extensions import db
from app.models import Job, User
from datetime import datetime
import decimal

def seed():
    print("🌱 Seeding jobs...")

    hr_id = User.query.filter_by(role='hr').first().id
    jobs = [
        Job(
            hr_user_id=hr_id,
            job_title="IT Data Engineer - TAF",
            job_location="Jakarta, Indonesia",
            job_description=(
                "Responsible for designing, developing, and maintaining data pipelines (ETL). "
                "Will work with large datasets, cloud platforms, and data warehousing solutions "
                "to support business intelligence and analytics at Toyota Astra Financial Services (TAF)."
            ),
            min_gpa=decimal.Decimal('3.20'), # Menggunakan Decimal untuk presisi
            min_experience=2,
            max_experience=5,
            degree_requirements="Bachelor's in Computer Science, Information Systems, or related field",
            requirements_json=[
                "Minimum 2 years of experience in data engineering or related roles.",
                "Proficiency in SQL and Python programming.",
                "Experience in designing and managing ETL processes.",
                "Familiar with data warehouse concepts.",
                "Experience with cloud platforms (AWS, GCP, or Azure) is a strong plus."
            ],
            created_at=datetime.utcnow(),
        ),
        Job(
            hr_user_id=hr_id,
            job_title="ERP Business Analyst Project - GSI",
            job_location="Jakarta, Indonesia",
            job_description=(
                "Act as a vital liaison between business stakeholders and the IT team for a large-scale ERP implementation project at PT Gaya Motor (GSI). "
                "Responsible for gathering user requirements, analyzing and mapping business processes, and ensuring the ERP solution (e.g., SAP) meets business needs."
            ),
            min_gpa=decimal.Decimal('3.25'),
            min_experience=3,
            max_experience=7,
            degree_requirements="Bachelor's in Information Systems, Industrial Engineering, or related field",
            requirements_json=[
                "Minimum 3 years of experience as a Business Analyst, preferably in ERP projects (SAP, Oracle, etc.).",
                "Strong understanding of core business processes (e.g., Finance, SCM, Manufacturing).",
                "Excellent communication and requirement gathering skills."
            ],
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
