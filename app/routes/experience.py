# backend-cv-analyzer/app/routes/experience.py
from flask import Blueprint, request, jsonify
from app.models import Candidate
from app.extensions import db
from sqlalchemy import func, distinct

experience_bp = Blueprint('experience', __name__)

@experience_bp.route('/api/experience/autocomplete', methods=['GET'])
def autocomplete_experience():
    query = request.args.get('q', '').strip().lower()
    
    if not query or len(query) < 2:
        return jsonify({'data': []})
    
    try:
        # Cari job titles/experience yang mengandung query (case insensitive)
        experiences = (
            db.session.query(
                distinct(func.lower(Candidate.experience)).label('experience')
            )
            .filter(func.lower(Candidate.experience).like(f"%{query}%"))
            .limit(10)
            .all()
        )
        
        # Extract job titles dari experience field
        results = []
        for exp in experiences:
            if exp.experience:
                # Coba extract job title dari experience string
                experience_text = exp.experience.lower()
                if query in experience_text:
                    # Ambil bagian yang relevan (sekitar query)
                    results.append({
                        "id": len(results),  # Simple ID
                        "name": exp.experience[:100]  # Batasi panjang
                    })
        
        return jsonify({'data': results})
        
    except Exception as e:
        print(f"Error in autocomplete_experience: {e}")
        return jsonify({'data': []})