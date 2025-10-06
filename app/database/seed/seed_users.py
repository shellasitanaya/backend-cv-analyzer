from app.extensions import db
from app.models import User
from datetime import datetime
from flask_bcrypt import generate_password_hash

def seed():
    print("🌱 Seeding users...")

    users = [
        User(
            name="Admin HR 1",
            email="hr1@example.com",
            password=generate_password_hash("password123"),
            role="hr",
            created_at=datetime.utcnow()
        ),
        User(
            name="Admin HR 2",
            email="hr2@example.com",
            password=generate_password_hash("password123"),
            role="hr",
            created_at=datetime.utcnow()
        ),
        User(
            name="Candidate User",
            email="candidate@example.com",
            password=generate_password_hash("password123"),
            role="user",
            created_at=datetime.utcnow()
        ),
    ]

    # prevent duplicates
    for user in users:
        existing = User.query.filter_by(email=user.email).first()
        if not existing:
            db.session.add(user)

    db.session.commit()
    print("✅ Users seeded successfully!")
