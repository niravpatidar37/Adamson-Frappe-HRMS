"""Tests for intake validation (malware/type/size checks)."""

import pytest

from screening.core.exceptions import UntrustedContentError
from screening.services.intake_service import validate_upload


def test_rejects_unsupported_content_type() -> None:
    with pytest.raises(UntrustedContentError):
        validate_upload("image/png", 100, b"\x89PNG", max_bytes=1000)


def test_rejects_oversized_file() -> None:
    with pytest.raises(UntrustedContentError):
        validate_upload("application/pdf", 2000, b"%PDF-1.4", max_bytes=1000)


def test_rejects_mismatched_pdf_signature() -> None:
    with pytest.raises(UntrustedContentError):
        validate_upload("application/pdf", 100, b"not-a-pdf", max_bytes=1000)


def test_accepts_valid_pdf() -> None:
    validate_upload("application/pdf", 100, b"%PDF-1.4", max_bytes=1000)
