# backend-cv-analyzer/app/routes/skills.py
from flask import Blueprint, request, jsonify
from app.models import Skill
from app.extensions import db
from sqlalchemy import func

skills_bp = Blueprint('skills', __name__)

@skills_bp.route('/api/skills/autocomplete', methods=['GET'])
def autocomplete_skills():
    query = request.args.get('q', '').strip().lower()
    
    print(f"🔍 Autocomplete request for: '{query}'")
    
    if not query or len(query) < 1:  # Ubah menjadi 1 karakter minimal
        return jsonify({'data': []})
    
    try:
        # Cari skill yang mengandung query (case insensitive)
        skills = (
            db.session.query(Skill)
            .filter(func.lower(Skill.skill_name).like(f"%{query}%"))
            .order_by(Skill.skill_name)
            .limit(15)  # Tambah limit menjadi 15
            .all()
        )
        
        results = [{"id": skill.id, "name": skill.skill_name} for skill in skills]
        print(f"✅ Found {len(results)} skills for '{query}': {[r['name'] for r in results]}")
        
        return jsonify({'data': results})
        
    except Exception as e:
        print(f"❌ Error in autocomplete_skills: {e}")
        return jsonify({'data': []}), 500