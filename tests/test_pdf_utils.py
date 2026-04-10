import fitz  # PyMuPDF
from app.services.pdf_utils import pdf_all_pages_to_jpeg


JPEG_MAGIC = b"\xff\xd8\xff"


def test_all_pages_returns_jpeg_per_page():
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page(width=200, height=200)
        page.insert_text((50, 100), f"Page {i + 1}")
    pdf_bytes = doc.tobytes()
    doc.close()

    pages = pdf_all_pages_to_jpeg(pdf_bytes)

    assert len(pages) == 3
    for jpeg in pages:
        assert jpeg[:3] == JPEG_MAGIC
        assert len(jpeg) > 100


def test_all_pages_single_page_pdf():
    doc = fitz.open()
    doc.new_page(width=200, height=200)
    pdf_bytes = doc.tobytes()
    doc.close()

    pages = pdf_all_pages_to_jpeg(pdf_bytes)

    assert len(pages) == 1
    assert pages[0][:3] == JPEG_MAGIC
