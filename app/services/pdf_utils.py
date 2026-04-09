import fitz  # PyMuPDF


def pdf_first_page_to_png(pdf_bytes: bytes) -> bytes:
    """Extract the first page of a PDF as a PNG image."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[0]
    # Render at 2x resolution for good quality
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    png_bytes = pix.tobytes("png")
    doc.close()
    return png_bytes
