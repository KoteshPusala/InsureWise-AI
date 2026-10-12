import os
import io
import fitz
try:
    from PIL import Image
    import pytesseract
except ImportError:
    pass

from config import settings

def is_tesseract_available() -> bool:
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False

def extract_pdf_text(file_path: str) -> dict:
    if not os.path.exists(file_path):
        raise ValueError(f"File not found: {file_path}")
        
    try:
        doc = fitz.open(file_path)
    except Exception as e:
        raise ValueError(f"Corrupt or unreadable PDF: {str(e)}")
        
    if doc.is_encrypted:
        doc.close()
        raise ValueError("This PDF is password-protected or encrypted. Please upload an unencrypted document.")
        
    if len(doc) == 0:
        doc.close()
        raise ValueError("The uploaded PDF is empty (0 pages).")
        
    pages = []
    ocr_pages = []
    tesseract_available = is_tesseract_available()
    
    max_pages = getattr(settings, "MAX_PAGES", 200)
    total_pages = min(len(doc), max_pages)
    
    min_chars = getattr(settings, "OCR_MIN_CHARS", 30)
    
    for page_num in range(total_pages):
        page = doc[page_num]
        text = page.get_text() or ""
        is_ocr = False
        
        # Only run OCR if extractable text is below the threshold
        if len(text.strip()) < min_chars:
            if tesseract_available:
                try:
                    pix = page.get_pixmap()
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    ocr_text = pytesseract.image_to_string(img)
                    if ocr_text and len(ocr_text.strip()) > len(text.strip()):
                        text = ocr_text
                        is_ocr = True
                        ocr_pages.append(page_num + 1)
                except Exception:
                    pass
                    
        pages.append({
            "page_number": page_num + 1,
            "text": text,
            "is_ocr": is_ocr
        })
        
    doc.close()
    
    total_readable_chars = sum(len(p["text"].strip()) for p in pages)
    if total_readable_chars < 30:
        if not tesseract_available:
            raise ValueError(
                "Scanned-only PDF detected with no extractable text, and OCR (Tesseract) is unavailable on the server. "
                "Please upload a searchable text PDF."
            )
        else:
            raise ValueError(
                "No readable text could be extracted from this PDF. "
                "The file may be blank, unreadable image scans, or corrupt."
            )
    
    return {
        "pages": pages,
        "total_pages": total_pages,
        "ocr_pages": ocr_pages
    }
