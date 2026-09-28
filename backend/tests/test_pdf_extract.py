import io
from reportlab.pdfgen import canvas
from app.services.pdf_extract import extract_text_from_pdf


def _make_pdf_bytes(lines):
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    y = 800
    for line in lines:
        c.drawString(72, y, line)
        y -= 20
    c.save()
    return buf.getvalue()


def test_extract_text_from_pdf_returns_expected_text():
    pdf_bytes = _make_pdf_bytes(["Hello DocuMind", "Second line of text"])
    text = extract_text_from_pdf(pdf_bytes)
    assert "Hello DocuMind" in text
    assert "Second line of text" in text


def test_extract_text_from_pdf_multi_page():
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 800, "Page one content")
    c.showPage()
    c.drawString(72, 800, "Page two content")
    c.save()
    text = extract_text_from_pdf(buf.getvalue())
    assert "Page one content" in text
    assert "Page two content" in text
