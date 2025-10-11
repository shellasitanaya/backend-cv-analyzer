from app.extensions import db
from app.models import Candidate, Job
from datetime import datetime
import uuid

def seed():
    print("🌱 Seeding candidates...")

    job = Job.query.first()
    if not job:
        print("⚠️ No jobs found! Please seed jobs first.")
        return


    candidates = [
        Candidate(
            id=str(uuid.uuid4()),
            job_id=job.id,  # pastikan ini sesuai ID job yang ada di tabel jobs
            original_filename="cv_john_doe.pdf",
            storage_path="/uploads/cv_john_doe.pdf",
            extracted_name="John Doe",
            extracted_email="john@example.com",
            extracted_phone="+628123456789",
            match_score=87.5,
            structured_profile_json={
                "hard_skills": ["Python", "HTML", "CSS", "SQL", "Flask"]
            },
            education="Bachelor of Computer Science, University of Indonesia (2020-2024)",
            experience="Backend Developer at ABC Corp (2023-2024)",
            status="passed_filter",
            uploaded_at=datetime.utcnow()
        ),
        Candidate(
            id=str(uuid.uuid4()),
            job_id=job.id, # bisa ubah kalau ada job lain
            original_filename="cv_jane_smith.pdf",
            storage_path="/uploads/cv_jane_smith.pdf",
            extracted_name="Jane Smith",
            extracted_email="jane@example.com",
            extracted_phone="+628987654321",
            match_score=76.3,
            structured_profile_json={
                "hard_skills": ["JavaScript", "React", "Node.js", "Flask"]
            },
            education="Bachelor of Creative Media Communication, University of Surabaya (2018-2022)",
            experience="Real Estate Agent (2021-2023)",
            status="processing",
            uploaded_at=datetime.utcnow()
        ),
        Candidate(
            id=str(uuid.uuid4()),
            job_id=job.id, # bisa ubah kalau ada job lain
            original_filename="cv_gilberto_poetro.pdf",
            storage_path="/uploads/cv_gilberto_poetro.pdf",
            extracted_name="Gilberto Poetro",
            extracted_email="toto@example.com",
            extracted_phone="+628987654321",
            match_score=92.9,
            structured_profile_json={
                "hard_skills": ["JavaScript", "React", "Python", "HTML", "Flask"]
            },
            education="Infor, UKP (2023-2027)",
            experience="Full Time Monoploy Player (Dari Lahir)",
            status="processing",
            uploaded_at=datetime.utcnow()
        ),
    ]

    for candidate in candidates:
        existing = Candidate.query.filter_by(extracted_email=candidate.extracted_email).first()
        if not existing:
            db.session.add(candidate)

    db.session.commit()
    print("✅ Candidates seeded successfully!")
