"""Rasterise a document into page images for the vision model.

pypdfium2 rather than pdf2image: no poppler binary to install, and it ships
manylinux wheels, so the worker image needs no system packages.

A document over the page cap is NOT truncated. Screening the first four pages
of a nine-page resume silently drops whatever was on the rest, and the
candidate would never know which half was read. Over the cap goes to human
review, the same way an UNKNOWN eligibility result does.
"""

import io

import pypdfium2

from screening.core.exceptions import UntrustedContentError

# 150 DPI. Enough for a vision model to read body text on a resume, while
# keeping the token count per page down — that count, not the weights, is
# what exhausts a GPU.
_RENDER_SCALE = 150 / 72


class DocumentTooLongError(Exception):
    """Over the page cap. Route to human review, never to rejection."""

    def __init__(self, pages: int, limit: int) -> None:
        super().__init__(f"document has {pages} pages, limit is {limit}")
        self.pages = pages
        self.limit = limit


class UnsupportedDocumentError(Exception):
    """A format nothing here can rasterise. Human review, not rejection."""


def render_pdf_pages(data: bytes, *, max_pages: int) -> list[bytes]:
    """Return one PNG per page, in order."""
    try:
        document = pypdfium2.PdfDocument(data)
    except Exception as exc:  # pypdfium2 raises its own types for bad input
        # The bytes passed the magic-byte check at intake and still will not
        # open, so they are malformed rather than merely unexpected.
        raise UntrustedContentError("file is not a readable PDF") from exc

    try:
        page_count = len(document)
        if page_count > max_pages:
            raise DocumentTooLongError(page_count, max_pages)

        images: list[bytes] = []
        for index in range(page_count):
            page = document[index]
            bitmap = page.render(scale=_RENDER_SCALE)
            buffer = io.BytesIO()
            bitmap.to_pil().save(buffer, format="PNG")
            images.append(buffer.getvalue())
        return images
    finally:
        document.close()


def render_pages(data: bytes, *, content_type: str, max_pages: int) -> list[bytes]:
    if content_type == "application/pdf":
        return render_pdf_pages(data, max_pages=max_pages)
    # DOCX would need LibreOffice in the image to rasterise faithfully. Until
    # that is decided, a DOCX is a document a human reads, not one the model
    # silently mis-handles.
    raise UnsupportedDocumentError(f"cannot rasterise {content_type}")
