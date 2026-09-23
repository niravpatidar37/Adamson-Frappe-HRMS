"""Ingestion: accept a resume, return a receipt, queue the real work.

The contract with Frappe is that this answers fast. Frappe dispatches from a
background job, but the applicant record is already saved by then and a slow
engine must not back up Frappe's queue.

Frappe POSTs the file bytes rather than a URL for the engine to fetch. A URL
would be either unauthenticated (candidate PII on an open endpoint) or would
need engine credentials into Frappe. Pushing the bytes avoids both.
"""

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.config import Settings, get_settings
from app.security import verify_signature
from screening.core.exceptions import UntrustedContentError
from screening.services import intake_service

router = APIRouter()

_CHUNK = 1024 * 1024


async def _read_capped(upload: UploadFile, max_bytes: int) -> bytes:
    """Bound memory at max_bytes + one chunk.

    `await upload.read()` with no argument buffers the whole body before the
    limit can be checked, which defeats the limit.
    """
    chunks: list[bytes] = []
    total = 0
    while chunk := await upload.read(_CHUNK):
        total += len(chunk)
        if total > max_bytes:
            raise UntrustedContentError("file exceeds maximum allowed size")
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/intake", status_code=status.HTTP_202_ACCEPTED)
async def intake(
    applicant_id: str = Form(...),
    job_opening_id: str = Form(...),
    resume: UploadFile = File(...),
    _: None = Depends(verify_signature),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    data = await _read_capped(resume, settings.max_upload_bytes)
    try:
        intake_service.validate_upload(
            content_type=resume.content_type or "",
            size_bytes=len(data),
            head=data[:16],
            max_bytes=settings.max_upload_bytes,
        )
    except UntrustedContentError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "rejected upload") from exc

    receipt_id = str(uuid.uuid4())
    checksum = intake_service.checksum(data)

    # TODO(spike): persist the receipt and hand the bytes to the worker.
    # Blocked on spike question 5 — where quarantined files live before a
    # scanner has looked at them. Writing them anywhere before that is
    # decided would be the path-traversal mistake again, in a new place.

    return {
        "receipt_id": receipt_id,
        "applicant_id": applicant_id,
        "job_opening_id": job_opening_id,
        "checksum_sha256": checksum,
        "status": "accepted",
    }
