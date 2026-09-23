"""The pipeline, from a quarantined PDF to an audit row.

The model call is replaced with a fake. Everything else is the real code
path: rendering, validation, the minimization boundary, the audit write and
the receipt's final state. The HTTP transport is covered separately by the
payload tests, which assert on what would go over the wire.
"""

import io
import uuid

import pypdfium2
import pytest

FIXTURE_PROFILE = """{
  "full_name": "Jordan Avery",
  "emails": ["jordan.avery@example.com"],
  "phones": ["+1-555-0100"],
  "skills": [{"name": "Python"}, {"name": "PostgreSQL"}],
  "experiences": [
    {"title": "Senior Engineer", "company": "Northwind",
     "start_date": "2021-03-01", "end_date": null}
  ],
  "educations": [{"institution": "University of Toronto", "degree": "BSc"}],
  "certificates": [{"name": "AWS Solutions Architect"}]
}"""


def pdf_of(pages: int) -> bytes:
    document = pypdfium2.PdfDocument.new()
    for _ in range(pages):
        document.new_page(595, 842)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


@pytest.fixture
def fake_parser(monkeypatch):
    """Replace the model, not the service around it."""

    def install(output: str):
        from app.workers import tasks

        class FakeClient:
            def __init__(self, **_kwargs):
                pass

            async def parse(self, page_images, **_kwargs):
                self.pages_seen = len(page_images)
                return output

        monkeypatch.setattr(tasks, "ResumeParserClient", FakeClient)

    return install


def make_receipt(pages: int = 2) -> str:
    """Put a real PDF in quarantine and commit a receipt pointing at it."""
    from app.config import get_settings
    from app.db.models import ScreeningReceipt
    from app.db.session import get_session_factory
    from app.storage import save_quarantined

    settings = get_settings()
    receipt_id = uuid.uuid4()
    data = pdf_of(pages)
    object_key = save_quarantined(
        root=settings.quarantine_root, receipt_id=receipt_id, filename="cv.pdf", data=data
    )
    with get_session_factory()() as session:
        session.add(
            ScreeningReceipt(
                id=receipt_id,
                applicant_id=str(uuid.uuid4()),
                job_opening_id="HR-OPN-2026-0001",
                checksum_sha256="0" * 64,
                original_filename="cv.pdf",
                content_type="application/pdf",
                object_key=object_key,
                idempotency_key=f"pipeline:{receipt_id}",
                status="accepted",
            )
        )
        session.commit()
    return str(receipt_id)


def read_back(receipt_id: str):
    from sqlalchemy import select

    from app.db.models import ScorecardAudit, ScreeningReceipt
    from app.db.session import get_session_factory

    with get_session_factory()() as session:
        receipt = session.get(ScreeningReceipt, uuid.UUID(receipt_id))
        audits = list(
            session.scalars(
                select(ScorecardAudit).where(ScorecardAudit.receipt_id == uuid.UUID(receipt_id))
            )
        )
        return receipt, audits


def run(receipt_id: str) -> None:
    from app.workers.tasks import screen_resume

    screen_resume.run(receipt_id)


def test_a_parsed_resume_produces_one_audit_row(client, fake_parser):
    fake_parser(FIXTURE_PROFILE)
    receipt_id = make_receipt(pages=2)
    run(receipt_id)

    receipt, audits = read_back(receipt_id)
    assert len(audits) == 1
    assert audits[0].payload["pages_rendered"] == 2
    # No approved criteria exist for this opening, so no rule ran and the
    # audit row must not imply one did.
    assert audits[0].eligibility_outcome == "unknown"
    assert audits[0].criteria_version == 0
    assert audits[0].score is None
    assert receipt.status == "needs_review"


def test_the_stored_scoring_profile_carries_no_identifiers(client, fake_parser):
    """The minimization boundary, asserted rather than assumed. This is the
    exact object a scoring model would be handed."""
    fake_parser(FIXTURE_PROFILE)
    receipt_id = make_receipt()
    run(receipt_id)

    _, audits = read_back(receipt_id)
    stored = str(audits[0].scoring_profile)

    for identifier in ("Jordan", "Avery", "jordan.avery@example.com", "555-0100"):
        assert identifier not in stored
    # The things it is allowed to carry are still there.
    assert "Python" in stored
    assert "AWS Solutions Architect" in stored


def test_invalid_model_output_goes_to_review_not_rejection(client, fake_parser):
    """The candidate is not penalised for the model's output."""
    fake_parser("I'm sorry, I cannot read this document.")
    receipt_id = make_receipt()
    run(receipt_id)

    receipt, audits = read_back(receipt_id)
    assert receipt.status == "needs_review"
    assert audits == []
    # The raw output is not stored: unvalidated model text derived from
    # candidate PII.
    assert "sorry" not in (receipt.error_message or "").lower()


def test_a_document_over_the_page_cap_goes_to_review(client, fake_parser):
    fake_parser(FIXTURE_PROFILE)
    receipt_id = make_receipt(pages=9)
    run(receipt_id)

    receipt, audits = read_back(receipt_id)
    assert receipt.status == "needs_review"
    assert "9 pages" in receipt.error_message
    assert audits == []


def test_rerunning_a_finished_receipt_writes_no_second_row(client, fake_parser):
    """Celery redelivers on worker loss, and the audit table is append-only."""
    fake_parser(FIXTURE_PROFILE)
    receipt_id = make_receipt()
    run(receipt_id)
    run(receipt_id)

    _, audits = read_back(receipt_id)
    assert len(audits) == 1
