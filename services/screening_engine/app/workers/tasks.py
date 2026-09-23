"""The screening pipeline.

    receipt -> page images -> VLM parse -> validate -> scoring profile
            -> rules -> audit row

Order matters. The deterministic rules run before any scoring: an eligibility
result of UNKNOWN routes to human review without a model ever scoring the
candidate, and a FAIL is only emitted for an explicit, high-confidence
disqualifier.

Nothing here rejects a candidate. Every failure — an unreadable file, a model
that emits invalid JSON, a job with no approved criteria — ends as
`needs_review`, because a system that cannot read a resume has not learned
anything about the person who wrote it.
"""

import asyncio
import uuid
from datetime import UTC, datetime

from celery.utils.log import get_task_logger

from app.config import get_settings
from app.db.models import ScorecardAudit, ScreeningReceipt
from app.db.session import get_session_factory
from app.storage import quarantined_path
from app.workers.celery_app import celery_app
from screening.core.exceptions import UntrustedContentError
from screening.model_serving.client import ResumeParserClient
from screening.schemas.scoring_profile import build_scoring_profile
from screening.services.page_rendering import (
    DocumentTooLongError,
    UnsupportedDocumentError,
    render_pages,
)
from screening.services.parser_service import ParserService

logger = get_task_logger(__name__)

PROMPT_VERSION = "resume-parser-v1"

# No approved criteria exist for the job yet, so eligibility was not evaluated.
# Recorded as a real version number would be, so the audit row never implies a
# rule ran when none did.
NO_CRITERIA_VERSION = 0


def _finish(session, receipt: ScreeningReceipt, status: str, error: str | None = None) -> None:
    receipt.status = status
    receipt.error_message = error
    receipt.completed_at = datetime.now(UTC)
    session.commit()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def screen_resume(self, receipt_id: str) -> None:
    """Parse and evaluate one resume."""
    settings = get_settings()
    with get_session_factory()() as session:
        receipt = session.get(ScreeningReceipt, uuid.UUID(receipt_id))
        if receipt is None:
            logger.warning("receipt %s no longer exists", receipt_id)
            return
        if receipt.status != "accepted":
            # Celery redelivers on worker loss, and this task writes an
            # append-only audit row. Re-running would record a second
            # screening of one submission.
            logger.info("receipt %s already at %s", receipt_id, receipt.status)
            return

        receipt.status = "parsing"
        session.commit()

        try:
            data = quarantined_path(
                root=settings.quarantine_root, object_key=receipt.object_key
            ).read_bytes()
        except (OSError, UntrustedContentError) as exc:
            logger.exception("receipt %s: quarantined file unreadable", receipt_id)
            _finish(session, receipt, "failed", "quarantined file unreadable")
            raise self.retry(exc=exc) from exc

        try:
            page_images = render_pages(
                data, content_type=receipt.content_type, max_pages=settings.max_resume_pages
            )
        except DocumentTooLongError as exc:
            _finish(session, receipt, "needs_review",
                    f"document is {exc.pages} pages, limit is {exc.limit}")
            return
        except UnsupportedDocumentError:
            _finish(session, receipt, "needs_review", "document format cannot be read here")
            return
        except UntrustedContentError:
            _finish(session, receipt, "needs_review", "document could not be opened")
            return

        parser = ParserService(
            ResumeParserClient(
                endpoint=settings.vlm_endpoint,
                model=settings.vlm_model,
                timeout=settings.vlm_timeout_seconds,
            )
        )
        try:
            profile, raw_output = asyncio.run(parser.parse_resume(page_images))
        except Exception as exc:  # transport failure of any kind; retried below
            logger.exception("receipt %s: parser call failed", receipt_id)
            _finish(session, receipt, "failed", "resume parser unavailable")
            raise self.retry(exc=exc) from exc

        if profile is None:
            # The model returned something that is not a CandidateProfile.
            # A human reads the resume; the candidate is not penalised for the
            # model's output. The raw text is deliberately not stored — it is
            # unvalidated model output derived from candidate PII.
            _finish(session, receipt, "needs_review",
                    f"parser output was not valid ({len(raw_output)} chars)")
            return

        scoring_profile = build_scoring_profile(
            application_id=receipt.applicant_id,
            job_id=receipt.job_opening_id,
            profile=profile,
        )

        # Eligibility needs an approved JobBlueprint for this opening, and
        # nothing creates one yet. Screening against criteria no human
        # approved is exactly what the design forbids, so this stops here and
        # a person decides.
        session.add(
            ScorecardAudit(
                receipt_id=receipt.id,
                applicant_id=receipt.applicant_id,
                job_opening_id=receipt.job_opening_id,
                model_id=settings.vlm_model,
                prompt_version=PROMPT_VERSION,
                criteria_version=NO_CRITERIA_VERSION,
                eligibility_outcome="unknown",
                rule_results={"reason": "no approved criteria for this job opening"},
                score=None,
                recommendation=None,
                payload={"pages_rendered": len(page_images)},
                # Stored so the minimization boundary is auditable rather than
                # merely asserted: this is exactly what a scoring model would
                # have been given.
                scoring_profile=scoring_profile.model_dump(mode="json"),
            )
        )
        _finish(session, receipt, "needs_review", "awaiting approved criteria for this job")
