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
            job_id=job.id,
            original_filename="cv_john_doe.pdf",
            storage_path="/uploads/cv_john_doe.pdf",
            name="John Doe",
            email="john@example.com",
            phone="+628123456789",
            match_score=87.5,
            education="Bachelor of Computer Science, University of Indonesia (2020-2024)",
            experience="Backend Developer at ABC Corp (2023-2024)",
            status="passed_filter",
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
            education="Bachelor of Creative Media Communication, University of Surabaya (2018-2022)",
            experience="Real Estate Agent (2021-2023)",
            status="processing",
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
            education="Infor, UKP (2023-2027)",
            experience="Full Time Monopoly Player (Dari Lahir)",
            status="processing",
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
            education="Bachelor of Information Systems, BINUS University (2019-2023)",
            experience="Software Engineer at TechWorks (2022-2024)",
            status="passed_filter",
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
            education="Bachelor of Informatics, Telkom University (2018-2022)",
            experience="Junior Java Developer at FintechID (2022-2023)",
            status="processing",
            uploaded_at=datetime.utcnow()
        ),
        Candidate(
            id=str(uuid.uuid4()),
            job_id=job.id,
            original_filename="cv_sarah_lim.pdf",
            storage_path="/uploads/cv_sarah_lim.pdf",
            name="Sarah Lim",
            email="sarah@example.com",
            phone="+6281238905674",
            match_score=95.1,
            education="Bachelor of Computer Engineering, Petra Christian University (2020-2024)",
            experience="Frontend Developer Intern at EComLabs (2023-2024)",
            status="passed_filter",
            uploaded_at=datetime.utcnow()
        ),
        Candidate(
            id=str(uuid.uuid4()),
            job_id=job.id,
            original_filename="cv_daniel_kurniawan.pdf",
            storage_path="/uploads/cv_daniel_kurniawan.pdf",
            name="Daniel Kurniawan",
            email="daniel@example.com",
            phone="+6282199912345",
            match_score=79.2,
            education="Bachelor of IT, Universitas Ciputra (2019-2023)",
            experience="Software Developer at CloudLogic (2023-2024)",
            status="processing",
            uploaded_at=datetime.utcnow()
        ),
        Candidate(
            id=str(uuid.uuid4()),
            job_id=job.id,
            original_filename="cv_amelia_rahma.pdf",
            storage_path="/uploads/cv_amelia_rahma.pdf",
            name="Amelia Rahma",
            email="amelia@example.com",
            phone="+628129991234",
            match_score=88.3,
            education="Bachelor of Design, ITS (2019-2023)",
            experience="UI/UX Designer at Pixel Studio (2022-2024)",
            status="passed_filter",
            uploaded_at=datetime.utcnow()
        ),
        Candidate(
            id=str(uuid.uuid4()),
            job_id=job.id,
            original_filename="cv_david_hartono.pdf",
            storage_path="/uploads/cv_david_hartono.pdf",
            name="David Hartono",
            email="david@example.com",
            phone="+6282123457788",
            match_score=73.4,
            education="Bachelor of Computer Science, Universitas Kristen Duta Wacana (2019-2023)",
            experience="Web Developer at IDWorks (2022-2023)",
            status="processing",
            uploaded_at=datetime.utcnow()
        ),
        Candidate(
            id=str(uuid.uuid4()),
            job_id=job.id,
            original_filename="cv_meilani_putri.pdf",
            storage_path="/uploads/cv_meilani_putri.pdf",
            name="Meilani Putri",
            email="meilani@example.com",
            phone="+6281899888877",
            match_score=84.6,
            education="Bachelor of Statistics, Universitas Airlangga (2018-2022)",
            experience="Data Analyst at InsightLab (2022-2024)",
            status="passed_filter",
            uploaded_at=datetime.utcnow()
        ),
        Candidate(
            id=str(uuid.uuid4()),
            job_id=job.id,
            original_filename="cv_steven_lie.pdf",
            storage_path="/uploads/cv_steven_lie.pdf",
            name="Steven Lie",
            email="steven@example.com",
            phone="+6281288887777",
            match_score=89.9,
            education="Bachelor of Informatics, Universitas Parahyangan (2018-2022)",
            experience="Backend Developer at CloudX (2022-2024)",
            status="passed_filter",
            uploaded_at=datetime.utcnow()
        ),
        Candidate(
            id=str(uuid.uuid4()),
            job_id=job.id,
            original_filename="cv_nadia_anggraini.pdf",
            storage_path="/uploads/cv_nadia_anggraini.pdf",
            name="Nadia Anggraini",
            email="nadia@example.com",
            phone="+6281399998888",
            match_score=72.5,
            education="Bachelor of Computer Science, Universitas Atma Jaya (2019-2023)",
            experience="Frontend Developer Intern at Webly (2023-2024)",
            status="processing",
            uploaded_at=datetime.utcnow()
        ),
        Candidate(
            id=str(uuid.uuid4()),
            job_id=job.id,
            original_filename="cv_yusuf_hasan.pdf",
            storage_path="/uploads/cv_yusuf_hasan.pdf",
            name="Yusuf Hasan",
            email="yusuf@example.com",
            phone="+6282134456677",
            match_score=90.7,
            education="Bachelor of AI, Universitas Indonesia (2019-2023)",
            experience="Machine Learning Engineer at AIWorks (2023-2024)",
            status="passed_filter",
            uploaded_at=datetime.utcnow()
        ),
        Candidate(
            id=str(uuid.uuid4()),
            job_id=job.id,
            original_filename="cv_della_wardani.pdf",
            storage_path="/uploads/cv_della_wardani.pdf",
            name="Della Wardani",
            email="della@example.com",
            phone="+6281322234455",
            match_score=77.8,
            education="Bachelor of Business, Universitas Ciputra (2018-2022)",
            experience="Digital Marketer at BrandUp (2022-2024)",
            status="processing",
            uploaded_at=datetime.utcnow()
        ),
        Candidate(
            id=str(uuid.uuid4()),
            job_id=job.id,
            original_filename="cv_andre_setiawan.pdf",
            storage_path="/uploads/cv_andre_setiawan.pdf",
            name="Andre Setiawan",
            email="andre@example.com",
            phone="+6281399911223",
            match_score=83.2,
            education="Bachelor of Informatics, ITS (2019-2023)",
            experience="DevOps Engineer at NetInfra (2022-2024)",
            status="passed_filter",
            uploaded_at=datetime.utcnow()
        ),
        Candidate(
            id=str(uuid.uuid4()),
            job_id=job.id,
            original_filename="cv_rani_susanti.pdf",
            storage_path="/uploads/cv_rani_susanti.pdf",
            name="Rani Susanti",
            email="rani@example.com",
            phone="+6281788994455",
            match_score=65.5,
            education="Bachelor of English Literature, Universitas Padjadjaran (2017-2021)",
            experience="Content Specialist at EduTech (2022-2024)",
            status="processing",
            uploaded_at=datetime.utcnow()
        ),
        Candidate(
            id=str(uuid.uuid4()),
            job_id=job.id,
            original_filename="cv_tommy_halim.pdf",
            storage_path="/uploads/cv_tommy_halim.pdf",
            name="Tommy Halim",
            email="tommy@example.com",
            phone="+6281123344556",
            match_score=91.8,
            education="Bachelor of Mechatronics, Universitas Surabaya (2019-2023)",
            experience="Robotics Engineer at RoboLab (2023-2024)",
            status="passed_filter",
            uploaded_at=datetime.utcnow()
        ),
        Candidate(
            id=str(uuid.uuid4()),
            job_id=job.id,
            original_filename="cv_sinta_nuraini.pdf",
            storage_path="/uploads/cv_sinta_nuraini.pdf",
            name="Sinta Nuraini",
            email="sinta@example.com",
            phone="+6281155667788",
            match_score=80.6,
            education="Bachelor of Management, Universitas Brawijaya (2018-2022)",
            experience="Project Coordinator at SoftLink (2022-2024)",
            status="processing",
            uploaded_at=datetime.utcnow()
        ),
        Candidate(
            id=str(uuid.uuid4()),
            job_id=job.id,
            original_filename="cv_bagus_pangestu.pdf",
            storage_path="/uploads/cv_bagus_pangestu.pdf",
            name="Bagus Pangestu",
            email="bagus@example.com",
            phone="+6281299918776",
            match_score=86.4,
            education="Bachelor of Computer Science, Universitas Multimedia Nusantara (2020-2024)",
            experience="Frontend Engineer Intern at CodeHaus (2023-2024)",
            status="passed_filter",
            uploaded_at=datetime.utcnow()
        )
    ]

    for candidate in candidates:
        existing = Candidate.query.filter_by(email=candidate.email).first()
        if not existing:
            db.session.add(candidate)

    db.session.commit()
    print("✅ Candidates seeded successfully!")