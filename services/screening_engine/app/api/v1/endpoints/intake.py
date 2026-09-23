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
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.models import ScreeningReceipt
from app.db.session import get_db
from app.security import verify_signature
from app.storage import save_quarantined
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
    db: Session = Depends(get_db),
) -> dict[str, str]:
    try:
        data = await _read_capped(resume, settings.max_upload_bytes)
        intake_service.validate_upload(
            content_type=resume.content_type or "",
            size_bytes=len(data),
            head=data[:16],
            max_bytes=settings.max_upload_bytes,
        )
    except UntrustedContentError as exc:
        # The reason is deliberately not echoed: the caller is Frappe, and the
        # detail belongs in the engine's logs, not in a response a candidate's
        # file shaped.
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "rejected upload") from exc

    receipt_id = uuid.uuid4()
    checksum = intake_service.checksum(data)

    # Bytes to disk before the row, so a committed receipt always has a file
    # behind it. The reverse order can leave the worker chasing a missing one.
    object_key = save_quarantined(
        root=settings.quarantine_root,
        receipt_id=receipt_id,
        filename=resume.filename or "resume",
        data=data,
    )

    receipt = ScreeningReceipt(
        id=receipt_id,
        applicant_id=applicant_id,
        job_opening_id=job_opening_id,
        checksum_sha256=checksum,
        original_filename=(resume.filename or "resume")[:512],
        content_type=(resume.content_type or "")[:128],
        object_key=object_key,
        status="accepted",
    )
    db.add(receipt)
    db.commit()

    # TODO: enqueue screen_resume(receipt_id) once the pipeline lands. Queuing
    # now would only schedule a NotImplementedError and burn the retries.

    return {
        "receipt_id": str(receipt_id),
        "applicant_id": applicant_id,
        "job_opening_id": job_opening_id,
        "checksum_sha256": checksum,
        "status": "accepted",
    }
