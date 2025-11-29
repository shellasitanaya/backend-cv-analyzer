from app.extensions import db
from app.models import Candidate, Job
from datetime import datetime
import uuid
import json

def seed():
    print("🌱 Seeding candidates...")

    job = Job.query.first()
    if not job:
        print("⚠️ No jobs found! Please seed jobs first.")
        return

    candidates = [
        Candidate(
            id=str(uuid.uuid4()),
            job_id=job.id,
            original_filename="cv_john_doe.pdf",
            storage_path="/uploads/cv_john_doe.pdf",
            name="John Doe",
            email="john@example.com",
            phone="+628123456789",
            match_score=87.5,
            gpa=3.4,
            education="Bachelor of Computer Science, University of Indonesia (2020-2024)",
            experience=json.dumps(["Backend Developer at ABC Corp (2023-2024)"]),
            total_experience=1,
            status="passed_filter",
            scoring_reason="[Seeded Data] Cocok karena pengalaman di ABC Corp.", # <-- TAMBAHKAN
            uploaded_at=datetime.utcnow()
        ),
        Candidate(
            id=str(uuid.uuid4()),
            job_id=job.id,
            original_filename="cv_jane_smith.pdf",
            storage_path="/uploads/cv_jane_smith.pdf",
            name="Jane Smith",
            email="jane@example.com",
            phone="+628987654321",
            match_score=76.3,
            gpa=2.5,
            education="Bachelor of Creative Media Communication, University of Surabaya (2018-2022)",
            experience=json.dumps(["Real Estate Agent (2021-2023)"]),
            total_experience=2,
            status="processing",
            scoring_reason="[Seeded Data]", # <-- TAMBAHKAN
            uploaded_at=datetime.utcnow()
        ),
        Candidate(
            id=str(uuid.uuid4()),
            job_id=job.id,
            original_filename="cv_gilberto_poetro.pdf",
            storage_path="/uploads/cv_gilberto_poetro.pdf",
            name="Gilberto Poetro",
            email="toto@example.com",
            phone="+628987654321",
            match_score=92.9,
            gpa=3.91,
            education="Infor, UKP (2023-2027)",
            experience=json.dumps(["Full Time Monopoly Player (Dari Lahir)"]),
            total_experience=0,
            status="processing",
            scoring_reason="[Seeded Data]", # <-- TAMBAHKAN
            uploaded_at=datetime.utcnow()
        ),
        Candidate(
            id=str(uuid.uuid4()),
            job_id=job.id,
            original_filename="cv_maria_tan.pdf",
            storage_path="/uploads/cv_maria_tan.pdf",
            name="Maria Tan",
            email="maria@example.com",
            phone="+6281398765432",
            match_score=81.4,
            gpa=3.23,
            education="Bachelor of Information Systems, BINUS University (2019-2023)",
            experience=json.dumps(["Software Engineer at TechWorks (2022-2024)"]),
            total_experience=2,
            status="passed_filter",
            scoring_reason="[Seeded Data] Pengalaman sebagai Software Engineer.", # <-- TAMBAHKAN
            uploaded_at=datetime.utcnow()
        ),
        Candidate(
            id=str(uuid.uuid4()),
            job_id=job.id,
            original_filename="cv_rizky_firmansyah.pdf",
            storage_path="/uploads/cv_rizky_firmansyah.pdf",
            name="Rizky Firmansyah",
            email="rizky@example.com",
            phone="+6281212345678",
            match_score=68.9,
            gpa=1.1,
            education="Bachelor of Informatics, Telkom University (2018-2022)",
            experience=json.dumps(["Junior Java Developer at FintechID (2022-2023)"]),
            total_experience=1,
            status="processing",
            scoring_reason="[Seeded Data]", # <-- TAMBAHKAN
            uploaded_at=datetime.utcnow()
        ),
    ]

    for candidate in candidates:
        existing = Candidate.query.filter_by(email=candidate.email).first()
        if not existing:
            db.session.add(candidate)

    db.session.commit()
    print("✅ Candidates seeded successfully!")