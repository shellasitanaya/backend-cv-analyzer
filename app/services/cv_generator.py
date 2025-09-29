# filename: cv_generator.py
# location: backend-cv-analyzer/app/services/

import os
import uuid
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

# Tentukan base directory dari aplikasi
# Ini akan mengarah ke folder 'backend-cv-analyzer'
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

def create_cv_pdf(template_name: str, cv_data: dict) -> str:
    """
    Merender data CV ke template HTML, mengonversinya menjadi PDF, dan menyimpannya.

    Args:
        template_name (str): Nama template yang akan digunakan (misal: "modern").
        cv_data (dict): Data lengkap CV dari pengguna.

    Returns:
        str: Path relatif ke file PDF yang telah disimpan.
    """
    try:
        # 1. Setup Jinja2 Environment untuk memuat template
        # Kita memberitahu Jinja2 di mana harus mencari template
        template_dir = os.path.join(BASE_DIR, 'app', 'templates', 'cv')
        env = Environment(loader=FileSystemLoader(template_dir), autoescape=True)
        template = env.get_template(f'{template_name.lower()}.html')

        # 2. Render HTML dari template dengan data yang diberikan
        html_out = template.render(data=cv_data)

        # 3. Tentukan path dan nama file untuk output PDF
        # Kita buat nama file unik agar tidak saling menimpa
        unique_id = uuid.uuid4().hex[:8]
        output_filename = f"cv_{cv_data['personal_info']['full_name'].replace(' ', '_')}_{template_name}_{unique_id}.pdf"
        
        # Simpan file PDF di dalam folder 'static' agar bisa diakses dari web
        output_folder = os.path.join(BASE_DIR, 'app', 'static', 'generated_cvs')
        os.makedirs(output_folder, exist_ok=True) # Buat folder jika belum ada
        
        output_path = os.path.join(output_folder, output_filename)

        # 4. Konversi string HTML ke PDF menggunakan WeasyPrint
        HTML(string=html_out).write_pdf(output_path)
        
        # 5. Kembalikan path relatif yang bisa digunakan untuk URL
        # Contoh: 'app/static/generated_cvs/cv_John_Doe_modern_1234abcd.pdf'
        # akan diubah menjadi '/static/generated_cvs/cv_John_Doe_modern_1234abcd.pdf'
        relative_path = os.path.join('/static', 'generated_cvs', output_filename).replace('\\', '/')
        
        return relative_path

    except Exception as e:
        print(f"Error creating PDF: {e}")
        # Jika ada error, kembalikan None
        return None