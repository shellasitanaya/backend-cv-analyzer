import os
import fitz  #pyMuPDF
import docx


# def pdf_to_docx(pdf_path, docx_path):
#     """
#     Konversi file PDF ke DOCX.
#     """
#     if not os.path.exists(pdf_path):
#         print(f"Error: File tidak ditemukan di {pdf_path}")
#         return None

#     cv = Converter(pdf_path)
#     cv.convert(docx_path, start=0, end=None)  # konversi semua halaman
#     cv.close()
#     print(f"Berhasil konversi {pdf_path} → {docx_path}")
#     return docx_path

# def extract_text_from_docx(docx_path):
#     """
#     Mengekstrak teks dari file DOCX.
#     """
#     if not os.path.exists(docx_path):
#         print(f"Error: File tidak ditemukan di {docx_path}")
#         return None

#     doc = docx.Document(docx_path)
#     paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
#     full_text = "\n".join(paragraphs)
#     return full_text

def extract_text(file_path):
    """
    Mengekstrak teks dari file PDF (menggunakan PyMuPDF) atau DOCX.
    """
    try:
        if not os.path.exists(file_path):
            print(f"Error: File tidak ditemukan di {file_path}")
            return None

        # --- KEMBALI MENGGUNAKAN LOGIKA PyMuPDF UNTUK PDF ---
        if file_path.endswith('.pdf'):
            doc = fitz.open(file_path)
            all_blocks = []
            for page in doc:
                # Ekstrak teks sebagai blok dengan informasi posisi (koordinat)
                all_blocks.extend(page.get_text("blocks"))
            doc.close()
            
            # Urutkan blok dari atas ke bawah, lalu dari kiri ke kanan
            all_blocks.sort(key=lambda b: (b[1], b[0]))
            
            # Gabungkan kembali teks dari blok yang sudah diurutkan
            full_text = "\n".join([block[4] for block in all_blocks])
            return full_text

        # Logika untuk DOCX tetap sama
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

# =================================================================
# BAGIAN UNTUK TESTING
# =================================================================
if __name__ == '__main__':
    # 1. Dapatkan path absolut dari file ini (cv_parser.py)
    script_path = os.path.abspath(__file__)

    # 2. Dapatkan path ke folder root backend dengan "naik" beberapa level
    backend_root_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_path)))

    # 3. Gabungkan path root backend dengan folder 'test_cvs' dan nama file
    test_pdf_path = os.path.join(backend_root_dir, 'test_cvs', 'my_cv(2).pdf')
    test_docx_path = os.path.join(backend_root_dir, 'test_cvs', 'cv.docx')
    
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
        print(docx_text[:1000])  # tampilkan 1000 karakter pertama
