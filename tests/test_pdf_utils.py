import fitz  # PyMuPDF
from app.services.pdf_utils import pdf_first_page_to_png, pdf_all_pages_to_png


def test_extracts_first_page_as_png():
    # Create a minimal 1-page PDF in memory
    doc = fitz.open()
    page = doc.new_page(width=200, height=200)
    page.insert_text((50, 100), "Hello Sofject")
    pdf_bytes = doc.tobytes()
    doc.close()

    png_bytes = pdf_first_page_to_png(pdf_bytes)

    # Should be valid PNG (starts with PNG magic bytes)
    assert png_bytes[:4] == b"\x89PNG"
    assert len(png_bytes) > 100


def test_handles_multi_page_pdf():
    doc = fitz.open()
    doc.new_page(width=200, height=200)
    doc.new_page(width=200, height=200)
    pdf_bytes = doc.tobytes()
    doc.close()

    png_bytes = pdf_first_page_to_png(pdf_bytes)

    assert png_bytes[:4] == b"\x89PNG"


def test_all_pages_returns_png_per_page():
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page(width=200, height=200)
        page.insert_text((50, 100), f"Page {i + 1}")
    pdf_bytes = doc.tobytes()
    doc.close()

    pages = pdf_all_pages_to_png(pdf_bytes)

    assert len(pages) == 3
    for png in pages:
        assert png[:4] == b"\x89PNG"
        assert len(png) > 100


def test_all_pages_single_page_pdf():
    doc = fitz.open()
    doc.new_page(width=200, height=200)
    pdf_bytes = doc.tobytes()
    doc.close()

    pages = pdf_all_pages_to_png(pdf_bytes)

    assert len(pages) == 1
    assert pages[0][:4] == b"\x89PNG"
