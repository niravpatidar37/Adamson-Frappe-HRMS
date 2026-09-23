"""Ingestion: accept a resume, return a receipt, queue the real work.

The contract with Frappe is that this answers fast. Frappe dispatches from a
background job, but the applicant record is already saved by then and a slow
engine must not back up Frappe's queue.

Frappe POSTs the file bytes rather than a URL for the engine to fetch. A URL
would be either unauthenticated (candidate PII on an open endpoint) or would
need engine credentials into Frappe. Pushing the bytes avoids both.

Submission is idempotent. A network timeout on Frappe's side is indistinguishable
from a failure, so it will retry, and a retried resume must not become a second
screening of the same person.
"""

import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.models import ScreeningReceipt
from app.db.session import get_db
from app.security import verify_signature
from app.storage import quarantined_path, save_quarantined
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


def _receipt_body(receipt: ScreeningReceipt, *, replayed: bool) -> dict:
    return {
        # Both names for the same value: `receipt_id` is what the ledger and
        # the scorecard endpoint call it, `tracking_id` is what Frappe stores.
        "receipt_id": str(receipt.id),
        "tracking_id": str(receipt.id),
        "applicant_id": receipt.applicant_id,
        "job_opening_id": receipt.job_opening_id,
        "checksum_sha256": receipt.checksum_sha256,
        "status": receipt.status,
        "idempotent_replay": replayed,
    }


@router.post("/intake")
async def intake(
    response: Response,
    applicant_id: str = Form(...),
    job_opening_id: str = Form(...),
    resume: UploadFile = File(...),
    idempotency_key: str | None = Header(default=None),
    _: None = Depends(verify_signature),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> dict:
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

    checksum = intake_service.checksum(data)
    # Derived when the caller omits it. "The caller forgot" must not mean
    # "score this candidate twice".
    key = idempotency_key or f"{applicant_id}:{checksum}"

    existing = db.scalars(
        select(ScreeningReceipt).where(ScreeningReceipt.idempotency_key == key)
    ).first()
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return _receipt_body(existing, replayed=True)

    receipt_id = uuid.uuid4()
    filename = (resume.filename or "resume")[:512]

    # Bytes to disk before the row, so a committed receipt always has a file
    # behind it. The reverse order can leave the worker chasing a missing one.
    object_key = save_quarantined(
        root=settings.quarantine_root,
        receipt_id=receipt_id,
        filename=filename,
        data=data,
    )

    db.add(
        ScreeningReceipt(
            id=receipt_id,
            applicant_id=applicant_id,
            job_opening_id=job_opening_id,
            checksum_sha256=checksum,
            original_filename=filename,
            content_type=(resume.content_type or "")[:128],
            object_key=object_key,
            idempotency_key=key,
            status="accepted",
        )
    )
    try:
        db.commit()
    except IntegrityError:
        # Two concurrent retries both passed the SELECT above. The unique
        # index is what actually decides; this one lost, so it cleans up the
        # file it wrote and returns the winner's receipt.
        db.rollback()
        quarantined_path(root=settings.quarantine_root, object_key=object_key).unlink(
            missing_ok=True
        )
        winner = db.scalars(
            select(ScreeningReceipt).where(ScreeningReceipt.idempotency_key == key)
        ).first()
        if winner is None:
            raise
        response.status_code = status.HTTP_200_OK
        return _receipt_body(winner, replayed=True)

    # TODO: enqueue screen_resume(receipt_id) once the pipeline lands. Queuing
    # now would only schedule a NotImplementedError and burn the retries.

    response.status_code = status.HTTP_202_ACCEPTED
    return _receipt_body(
        db.get(ScreeningReceipt, receipt_id),  # type: ignore[arg-type]
        replayed=False,
    )
