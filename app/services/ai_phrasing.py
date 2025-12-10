# ai_phrasing.py - FIXED VERSION
import os
import google.generativeai as genai
from flask import Blueprint, request, jsonify
import logging
from datetime import datetime
import re
from dotenv import load_dotenv  # PENTING: Import ini

# Load environment variables dari file .env
load_dotenv()

# Konfigurasi logging
logger = logging.getLogger(__name__)

ai_phrasing_bp = Blueprint('ai_phrasing', __name__)

class GeminiAIPhraser:
    def __init__(self):
        # Ambil API KEY
        self.api_key = os.getenv('GEMINI_API_KEY')
        self.model = None
        
        # Debugging Print untuk memastikan Key terbaca
        if not self.api_key:
            print("❌ [AI PHRASER] CRITICAL: GEMINI_API_KEY is missing or empty!")
        else:
            print(f"✅ [AI PHRASER] API Key found (Length: {len(self.api_key)})")
            
        self.initialize_model()
    
    def initialize_model(self):
        try:
            if not self.api_key:
                logger.error("GEMINI_API_KEY not found in environment variables")
                return
            
            genai.configure(api_key=self.api_key)
            
            # URUTAN PRIORITAS MODEL (Gunakan 1.5 Flash karena 2.5 belum stabil/publik)
            model_candidates = [
                'gemini-2.5-flash-lite',
                'gemini-1.5-pro', 
                'gemini-pro',
                'models/gemini-1.5-flash'
            ]
            
            for model_name in model_candidates:
                try:
                    self.model = genai.GenerativeModel(model_name)
                    # Test generation sederhana untuk memastikan model hidup
                    # self.model.generate_content("Hi", generation_config={'max_output_tokens': 1})
                    print(f"✅ [AI PHRASER] Connected to model: {model_name}")
                    break
                except Exception as e:
                    print(f"⚠️ [AI PHRASER] Failed to connect to {model_name}: {e}")
                    continue
            
            if self.model:
                logger.info("Gemini AI model initialized successfully")
            else:
                print("❌ [AI PHRASER] Could not connect to any Gemini model.")
                
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}")
            print(f"❌ Failed to initialize Gemini model: {e}")
            self.model = None

    def _clean_input_text(self, text: str) -> str:
        """Clean input text before sending to AI"""
        if not text:
            return ""
        # Remove placeholder text and ellipsis
        text = re.sub(r'\b(adasasds|ddassd|\.\.\.)\b', '', text, flags=re.IGNORECASE)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _clean_and_format_bullet_points(self, text: str) -> str:
        """Clean AI output and ensure proper bullet point formatting"""
        if not text:
            return ""
        
        # Remove all markdown formatting except bullet points
        text = re.sub(r'[#`]', '', text) # Hapus hash dan backtick, TAPI JANGAN HAPUS * karena kadang jadi bullet
        
        # Remove quotes
        text = re.sub(r'^["\']|["\']$', '', text)
        
        # Remove ellipsis and placeholder text
        text = re.sub(r'\.\.\.', '.', text)
        text = re.sub(r'\b(adasasds|ddassd)\b', '', text, flags=re.IGNORECASE)
        
        # Split into lines
        lines = text.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Convert asterisks or dashes to bullets
            if line.startswith('* ') or line.startswith('- '):
                line = '• ' + line[2:]
            elif line.startswith('*') or line.startswith('-'):
                line = '• ' + line[1:]
            
            # Ensure bullet point formatting if not present
            if not line.startswith('•'):
                 # Cek apakah ini kalimat lanjutan atau poin baru.
                 # Asumsi AI disuruh bikin poin, jadi kita paksa poin.
                 line = '• ' + line
            
            # Ensure proper spacing after bullet
            if line.startswith('•') and len(line) > 1 and line[1] != ' ':
                line = '• ' + line[2:] if len(line) > 2 else line
            
            formatted_lines.append(line)
        
        return '\n'.join(formatted_lines).strip()

    def _ensure_bullet_formatting(self, text: str) -> str:
        """Ensure any text has proper bullet point formatting (Fallback logic)"""
        if not text:
            return ""
        
        # Split into sentences and add bullet points
        sentences = re.split(r'(?<=[.!?])\s+', text)
        formatted_lines = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 3:
                # Clean up the sentence
                sentence = re.sub(r'^[•\-*]\s*', '', sentence)  # Remove existing bullets
                formatted_lines.append(f"• {sentence}")
        
        return '\n'.join(formatted_lines)
    
    def phrase_summary(self, text, context=None):
        """AI phrasing untuk professional summary"""
        if not self.model:
            return self._ensure_bullet_formatting(text)
        
        text = self._clean_input_text(text)
        name = context.get('name', 'Candidate') if context else 'Candidate'
            
        prompt = f"""
        You are a professional career coach specializing in resume writing.
        
        TASK: Improve this CV summary to be professional, impactful and concise.
        
        ORIGINAL SUMMARY: {text}
        
        IMPORTANT FORMATTING REQUIREMENTS:
        1. MUST use bullet points with '•' symbol
        2. Each bullet point MUST be on its own line
        3. Each sentence should be a separate bullet point
        4. No paragraphs, only bullet points
        5. Start each bullet with '• ' (bullet symbol + space)
        
        IMPROVEMENT GUIDELINES:
        1. Start with a strong opening statement
        2. Highlight key expertise and experience
        3. Add realistic achievements (use metrics like: 20% improvement, 30% increase, etc.)
        4. Limit to 4-5 bullet points maximum
        5. Make it ATS-friendly with relevant keywords
        6. Focus on value proposition
        
        OUTPUT FORMAT EXAMPLE:
        • Results-oriented software engineer with 5+ years experience
        • Specialized in Python, Flask and scalable web applications
        • Improved system performance by 20% and user engagement by 15%
        • Seeking to leverage technical expertise in managerial role
        
        NAME CONTEXT: {name}
        
        IMPROVED SUMMARY (ONLY BULLET POINTS, ONE PER LINE):
        """
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3, # Sedikit lebih kreatif tapi tetap terarah
                    max_output_tokens=500,
                )
            )
            
            if response.text:
                return self._clean_and_format_bullet_points(response.text)
            else:
                return self._ensure_bullet_formatting(text)
        except Exception as e:
            logger.error(f"Error phrasing summary: {e}")
            print(f"❌ Error phrasing summary: {e}")
            return self._ensure_bullet_formatting(text)
    
    def phrase_experience(self, text, context=None):
        """AI phrasing untuk work experience"""
        if not self.model:
            return self._ensure_bullet_formatting(text)
        
        text = self._clean_input_text(text)
        job_title = context.get('job_title', 'Position') if context else 'Position'
        company = context.get('company', 'Organization') if context else 'Organization'
            
        prompt = f"""
        You are a professional resume writer.
        
        TASK: Rewrite this job description to focus on achievements with quantifiable results.
        
        ORIGINAL DESCRIPTION: {text}
        
        IMPORTANT FORMATTING REQUIREMENTS:
        1. MUST use bullet points with '•' symbol
        2. Each bullet point MUST be on its own line
        3. Each achievement should be a separate bullet point
        4. No paragraphs, only bullet points
        5. Start each bullet with '• ' (bullet symbol + space)
        
        IMPROVEMENT GUIDELINES:
        1. Convert responsibilities into achievements
        2. Start each bullet with strong action verbs (Developed, Implemented, Led, etc.)
        3. Add realistic metrics (15-40% improvements, specific numbers)
        4. Focus on outcomes, not just duties
        5. Structure as clear bullet points
        
        OUTPUT FORMAT EXAMPLE:
        • Developed and deployed Python/Flask applications serving 10K+ users
        • Improved data processing speed by 40% through optimization
        • Collaborated with cross-functional teams to deliver projects 25% ahead of schedule
        • Reduced critical errors by 15% through strategic improvements
        
        JOB CONTEXT: {job_title} at {company}
        
        IMPROVED JOB DESCRIPTION (ONLY BULLET POINTS, ONE PER LINE):
        """
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=500,
                )
            )
            
            if response.text:
                return self._clean_and_format_bullet_points(response.text)
            else:
                return self._ensure_bullet_formatting(text)
        except Exception as e:
            logger.error(f"Error phrasing experience: {e}")
            print(f"❌ Error phrasing experience: {e}")
            return self._ensure_bullet_formatting(text)

    def _improve_with_retry(self, text: str, text_type: str, context: dict = None, max_retries: int = 2) -> str:
        """Retry mechanism for AI improvements"""
        for attempt in range(max_retries):
            try:
                if text_type == 'summary':
                    improved = self.phrase_summary(text, context)
                elif text_type == 'experience':
                    improved = self.phrase_experience(text, context)
                else:
                    improved = self.phrase_summary(text, context)
                
                # Validasi hasil: harus ada bullet point dan panjang cukup
                if improved and len(improved) > 10 and '•' in improved:
                    return improved
            except Exception as e:
                logger.warning(f"⚠️ Attempt {attempt + 1} failed: {e}")
        
        return self._ensure_bullet_formatting(text)

# Inisialisasi AI Phraser
ai_phraser = GeminiAIPhraser()

@ai_phrasing_bp.route('ai-phrase', methods=['POST'])
def ai_phrase_text():
    """Endpoint utama untuk AI phrasing"""
    start_time = datetime.now()
    try:
        data = request.json
        text = data.get('text', '').strip()
        text_type = data.get('type', 'summary')
        context = data.get('context', {})
        
        print(f"\n🔍 [AI REQUEST] Type: {text_type} | Length: {len(text)}")
        
        if not text or len(text) < 3:
            return jsonify({'success': False, 'error': 'Text is too short'}), 400
        
        # Cek apakah model siap
        if ai_phraser.model is None:
            print("⚠️ [AI ERROR] Model not initialized. Check API KEY or Connection.")
            # Fallback manual
            formatted_text = ai_phraser._ensure_bullet_formatting(text)
            return jsonify({
                'success': True,
                'phrased_text': formatted_text,
                'using_fallback': True
            })
        
        # Proses dengan AI
        phrased_text = ai_phraser._improve_with_retry(text, text_type, context)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        print(f"✅ [AI SUCCESS] Generated {len(phrased_text)} chars in {processing_time:.2f}s")
        
        return jsonify({
            'success': True,
            'phrased_text': phrased_text,
            'original_length': len(text),
            'phrased_length': len(phrased_text),
            'processing_time': processing_time,
            'using_fallback': False
        })
        
    except Exception as e:
        logger.error(f"AI phrasing endpoint error: {e}")
        print(f"❌ [AI EXCEPTION] {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ai_phrasing_bp.route('ai-status', methods=['GET'])
def ai_status():
    """Check AI service status"""
    return jsonify({
        'status': 'operational' if ai_phraser.model else 'unavailable',
        'model_name': str(ai_phraser.model.model_name) if ai_phraser.model else None,
        'has_api_key': bool(ai_phraser.api_key)
    })