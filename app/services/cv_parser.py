import os
import fitz  #pyMuPDF
import docx


def extract_text(file_path):
    """
    Mengekstrak teks dari file PDF (menggunakan PyMuPDF) atau DOCX.
    """
    try:
        if not os.path.exists(file_path):
            print(f"Error: File tidak ditemukan di {file_path}")
            return None

        if file_path.endswith('.pdf'):
            doc = fitz.open(file_path)
            all_blocks = []
            for page in doc:
                all_blocks.extend(page.get_text("blocks"))
            doc.close()
            
            all_blocks.sort(key=lambda b: (b[1], b[0]))
            
            full_text = "\n".join([block[4] for block in all_blocks])
            return full_text

        elif file_path.endswith('.docx'):
            doc = docx.Document(file_path)
            full_text = []
            for para in doc.paragraphs:
                full_text.append(para.text)
            return '\n'.join(full_text)
        
        else:
            return None

    except Exception as e:
        print(f"Terjadi error saat memproses file {file_path}: {e}")
        return None


#  Testing
if __name__ == '__main__':
    # 1. Dapatkan path absolut dari file ini (cv_parser.py)
    script_path = os.path.abspath(__file__)

    # 2. Dapatkan path ke folder root backend dengan "naik" beberapa level
    backend_root_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_path)))

    # 3. Gabungkan path root backend dengan folder 'test_cvs' dan nama file
    test_pdf_path = os.path.join(backend_root_dir, 'test_cvs', 'my_cv(3).pdf')
    test_docx_path = os.path.join(backend_root_dir, 'test_cvs', 'my_cv(3).docx')
    
    print(f"Mencari file PDF di: {test_pdf_path}")
    print("--- Menguji File PDF ---")
    pdf_text = extract_text(test_pdf_path)
    if pdf_text:
        print(f"Berhasil mengekstrak {len(pdf_text)} karakter.\n")
        print(pdf_text)  # tampilkan 1000 karakter pertama biar tidak terlalu panjang

    print("\n" + "="*30 + "\n")

    print(f"Mencari file DOCX di: {test_docx_path}")
    print("--- Menguji File DOCX ---")
    docx_text = extract_text(test_docx_path)
    if docx_text:
        print(f"Berhasil mengekstrak {len(docx_text)} karakter.\n")
        print(docx_text[:3000])  # tampilkan 1000 karakter pertama
