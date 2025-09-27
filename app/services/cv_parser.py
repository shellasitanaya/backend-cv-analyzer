import fitz  # Ini adalah library PyMuPDF
import docx
import os

def extract_text(file_path):
    """
    Mengekstrak teks dari file PDF atau DOCX.

    Args:
        file_path (str): Path lengkap ke file yang akan diproses.

    Returns:
        str: Teks yang diekstrak dari file, atau None jika gagal.
    """
    try:
        if not os.path.exists(file_path):
            print(f"Error: File tidak ditemukan di {file_path}")
            return None

        # Memproses file .pdf
        if file_path.endswith('.pdf'):
            doc = fitz.open(file_path)
            full_text = ""
            for page in doc:
                full_text += page.get_text()
            doc.close()
            return full_text

        # Memproses file .docx
        elif file_path.endswith('.docx'):
            doc = docx.Document(file_path)
            full_text = []
            for para in doc.paragraphs:
                full_text.append(para.text)
            return '\n'.join(full_text)
        
        else:
            print(f"Error: Format file tidak didukung untuk {file_path}")
            return None

    except Exception as e:
        print(f"Terjadi error saat memproses file {file_path}: {e}")
        return None


# =================================================================
# BAGIAN UNTUK TESTING (Bisa dihapus nanti)
# =================================================================
if __name__ == '__main__':
    # Untuk menguji fungsi ini, buat folder 'test_cvs' di dalam folder 'backend'
    # Lalu letakkan beberapa file CV .pdf dan .docx di dalamnya.
    
    # Ganti nama file di bawah ini sesuai dengan file CV Anda
    test_pdf_path = r'C:\Users\Shella Valensia\OneDrive\Documents\GitHub\backend-cv-analyzer\test_cvs\my_cv(2).pdf'
    test_docx_path = r'C:\Users\Shella Valensia\OneDrive\Documents\GitHub\backend-cv-analyzer\test_cvs\my_cv.docx'
    
    print("--- Menguji File PDF ---")
    pdf_text = extract_text(test_pdf_path)
    if pdf_text:
        print(f"Berhasil mengekstrak {len(pdf_text)} karakter.\n")
        print(pdf_text[:500]) # Tampilkan 500 karakter pertama
        
    print("\n" + "="*30 + "\n")

    print("--- Menguji File DOCX ---")
    docx_text = extract_text(test_docx_path)
    if docx_text:
        print(f"Berhasil mengekstrak {len(docx_text)} karakter.\n")
        print(docx_text[:500]) # Tampilkan 500 karakter pertama