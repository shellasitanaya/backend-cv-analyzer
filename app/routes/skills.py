# backend-cv-analyzer/app/routes/skills.py
from flask import Blueprint, request, jsonify
from app.models import Skill, Candidate
from app.extensions import db
from sqlalchemy import func, distinct

skills_bp = Blueprint('skills', __name__)

@skills_bp.route('/api/skills/autocomplete', methods=['GET'])
def autocomplete_skills():
    query = request.args.get('q', '').strip().lower()
    
    print(f"🔍 Autocomplete request for: '{query}'")
    
    if not query or len(query) < 1:
        return jsonify({'data': []})
    
    try:
        # Cari skill yang mengandung query (case insensitive)
        skills = (
            db.session.query(Skill)
            .filter(func.lower(Skill.skill_name).like(f"%{query}%"))
            .order_by(Skill.skill_name)
            .limit(15)
            .all()
        )
        
        # Juga cari job titles/roles yang mengandung query
        experiences = (
            db.session.query(
                distinct(func.lower(Candidate.experience)).label('experience')
            )
            .filter(func.lower(Candidate.experience).like(f"%{query}%"))
            .limit(5)
            .all()
        )
        
        results = []
        
        # Tambahkan skills
        for skill in skills:
            results.append({
                "id": skill.id, 
                "name": skill.skill_name,
                "type": "skill"
            })
        
        # Tambahkan role suggestions
        for exp in experiences:
            if exp.experience and len(results) < 20:  # Batas total
                # Extract kemungkinan job title dari experience
                exp_lower = exp.experience.lower()
                if any(role_word in exp_lower for role_word in ['developer', 'engineer', 'designer', 'manager', 'analyst']):
                    results.append({
                        "id": f"role_{len(results)}",
                        "name": exp.experience[:50],  # Batasi panjang
                        "type": "role"
                    })
        
        print(f"✅ Found {len(results)} suggestions for '{query}'")
        
        return jsonify({'data': results})
        
    except Exception as e:
        print(f"❌ Error in autocomplete_skills: {e}")
        return jsonify({'data': []}), 500