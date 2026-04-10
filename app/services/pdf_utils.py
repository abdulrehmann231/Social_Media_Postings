import fitz  # PyMuPDF


def pdf_all_pages_to_jpeg(pdf_bytes: bytes) -> list[bytes]:
    """Render every PDF page as a JPEG at native resolution.

    JPEGs at 1x scale keep the multi-page payload small enough to fit
    inside the Groq vision request body limit (PNG at 2x hits 413).
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages: list[bytes] = []
    for page in doc:
        pix = page.get_pixmap()
        pages.append(pix.tobytes("jpeg"))
    doc.close()
    return pages
