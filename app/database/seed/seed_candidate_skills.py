from app.extensions import db
from app.models import Candidate, Skill, CandidateSkill
import uuid
import random

def seed():
    print("🌱 Seeding candidate_skills (using skill IDs from Skill table)...")

    candidates = Candidate.query.all()
    skills = Skill.query.all()

    if not candidates:
        print("⚠️ No candidates found! Please seed candidates first.")
        return
    if not skills:
        print("⚠️ No skills found! Please seed skills first.")
        return

    created_links = 0
    for candidate in candidates:
        # Randomly pick 3–8 skills for each candidate
        selected_skills = random.sample(skills, random.randint(3, 8))

        for skill in selected_skills:
            existing = CandidateSkill.query.filter_by(
                candidate_id=candidate.id,
                skill_id=skill.id
            ).first()

            if not existing:
                db.session.add(CandidateSkill(
                    id=str(uuid.uuid4()),
                    candidate_id=candidate.id,
                    skill_id=skill.id
                ))
                created_links += 1

    db.session.commit()
    print(f"✅ Created {created_links} candidate-skill links successfully!")

