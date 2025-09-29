# filename: openai_service.py
# location: backend-cv-analyzer/app/services/

import os
from openai import OpenAI
from dotenv import load_dotenv

# Muat environment variables dari file .env, terutama OPENAI_API_KEY
load_dotenv()

# Pastikan Anda sudah menambahkan OPENAI_API_KEY='kunci_api_anda' di file .env
# Inisialisasi klien OpenAI
try:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
except Exception as e:
    print(f"Error initializing OpenAI client: {e}")
    client = None

def get_phrasing_suggestion(text_input: str, context: str = "work_experience") -> str:
    """
    Menggunakan LLM (GPT) untuk memperbaiki atau memperindah kalimat untuk CV.

    Args:
        text_input (str): Teks asli dari pengguna.
        context (str): Konteks dari teks tersebut (misal: 'work_experience', 'summary').

    Returns:
        str: Teks hasil perbaikan dari AI.
    """
    if not client:
        return "OpenAI client is not initialized. Please check your API key."

    if not text_input or not text_input.strip():
        return ""

    # Prompt Template: Ini adalah instruksi yang kita berikan kepada AI.
    # Kita membuatnya dinamis berdasarkan konteks untuk hasil yang lebih baik.
    if context == "work_experience":
        prompt_template = f"""
        You are a professional resume writer. Your task is to rewrite the following job description to be more action-oriented and impactful for a CV. 
        Use strong action verbs and quantify achievements where possible. Keep it concise, professional, and clear.
        
        Original description: "{text_input}"
        
        Improved description (provide only the final text):
        """
    else: # Default prompt untuk summary atau konteks lain
        prompt_template = f"""
        You are a professional career coach. Your task is to rewrite the following professional summary to be more compelling and concise for a CV.
        Highlight key skills and experiences effectively.
        
        Original summary: "{text_input}"
        
        Improved summary (provide only the final text):
        """

    try:
        # Mengirim request ke API OpenAI
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Anda bisa ganti dengan model lain jika perlu
            messages=[
                {"role": "system", "content": "You are a helpful assistant for CV writing."},
                {"role": "user", "content": prompt_template}
            ],
            temperature=0.7, # Sedikit kreativitas
            max_tokens=150 # Batasi panjang output
        )
        
        # Mengambil hasil teks dari response AI
        suggested_text = completion.choices[0].message.content.strip()
        return suggested_text
    except Exception as e:
        print(f"An error occurred while calling OpenAI API: {e}")
        # Jika ada error, kembalikan teks asli sebagai fallback
        return f"Error processing text. Original: {text_input}"