"""Rasterising documents for the vision model."""

import io

import pypdfium2
import pytest

from screening.core.exceptions import UntrustedContentError
from screening.services.page_rendering import (
    DocumentTooLongError,
    UnsupportedDocumentError,
    render_pages,
    render_pdf_pages,
)


def pdf_of(page_count: int) -> bytes:
    """Build a real PDF rather than a fixture file, so the test says what it
    depends on."""
    document = pypdfium2.PdfDocument.new()
    for _ in range(page_count):
        document.new_page(595, 842)  # A4 at 72 dpi
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def test_each_page_becomes_one_png():
    images = render_pdf_pages(pdf_of(3), max_pages=4)
    assert len(images) == 3
    # PNG magic, so this is an image and not an error string that happens to
    # be bytes.
    assert all(image.startswith(b"\x89PNG\r\n\x1a\n") for image in images)


def test_a_document_over_the_cap_is_not_truncated():
    """Screening the first four pages of a nine-page resume silently drops
    the rest, and the candidate never learns which half was read."""
    with pytest.raises(DocumentTooLongError) as excinfo:
        render_pdf_pages(pdf_of(9), max_pages=4)
    assert excinfo.value.pages == 9
    assert excinfo.value.limit == 4


def test_a_document_exactly_at_the_cap_is_rendered():
    assert len(render_pdf_pages(pdf_of(4), max_pages=4)) == 4


def test_bytes_that_are_not_a_pdf_are_rejected():
    with pytest.raises(UntrustedContentError):
        render_pdf_pages(b"%PDF-1.7 and then nothing valid at all", max_pages=4)


def test_docx_is_unsupported_rather_than_silently_mishandled():
    docx = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    with pytest.raises(UnsupportedDocumentError):
        render_pages(b"PK\x03\x04", content_type=docx, max_pages=4)
