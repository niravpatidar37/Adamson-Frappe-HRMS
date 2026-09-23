"""Intake service (system-design.md section 7.3).

Validates uploads, stores them in quarantine object storage, and emits a
processing event. Never parses documents synchronously.
"""

import hashlib
from dataclasses import dataclass

from screening.core.exceptions import UntrustedContentError

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
# Magic-byte signatures for basic file-type verification (defense in depth
# beyond extension/MIME checks per system-design.md 11.6).
_PDF_MAGIC = b"%PDF-"
_DOCX_MAGIC = b"PK\x03\x04"


@dataclass(frozen=True, slots=True)
class IntakeResult:
    object_storage_key: str
    checksum_sha256: str


def validate_upload(content_type: str, size_bytes: int, head: bytes, max_bytes: int) -> None:
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise UntrustedContentError(f"unsupported content type: {content_type}")
    if size_bytes > max_bytes:
        raise UntrustedContentError("file exceeds maximum allowed size")
    if content_type == "application/pdf" and not head.startswith(_PDF_MAGIC):
        raise UntrustedContentError("file signature does not match PDF")
    if content_type != "application/pdf" and not head.startswith(_DOCX_MAGIC):
        raise UntrustedContentError("file signature does not match DOCX")


def checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
