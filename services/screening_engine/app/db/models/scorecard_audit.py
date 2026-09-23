"""Screening receipts and scorecards.

Append-only by intent (system-design.md 11.9): rows record what the system
decided at a point in time, against a criteria version that was active then.
Re-screening writes a new row rather than editing an old one, so a decision
can always be reconstructed as it was made.

No `updated_at` on purpose. A mutable audit record is not an audit record.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JSONVariant, TimestampMixin, UUIDPrimaryKeyMixin


class ScreeningReceipt(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Issued at intake, before any processing. Gives Frappe something to
    reference while the work is still queued, and gives a failed run somewhere
    to record why."""

    __tablename__ = "screening_receipts"

    # Frappe's identifiers. Foreign to this database by design: the engine
    # does not own applicants and must not assume they still exist.
    applicant_id: Mapped[str] = mapped_column(String(140), index=True)
    job_opening_id: Mapped[str] = mapped_column(String(140), index=True)

    checksum_sha256: Mapped[str] = mapped_column(String(64))
    original_filename: Mapped[str] = mapped_column(String(512))
    # Where the quarantined bytes are, relative to settings.quarantine_root.
    object_key: Mapped[str] = mapped_column(String(512))
    content_type: Mapped[str] = mapped_column(String(128))

    status: Mapped[str] = mapped_column(String(32), default="accepted", index=True)
    # accepted -> parsing -> scored | needs_review | failed
    error_message: Mapped[str | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ScorecardAudit(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "scorecard_audits"

    receipt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("screening_receipts.id", ondelete="RESTRICT"), index=True
    )
    applicant_id: Mapped[str] = mapped_column(String(140), index=True)
    job_opening_id: Mapped[str] = mapped_column(String(140), index=True)

    # What produced this, so a score can be explained months later.
    model_id: Mapped[str] = mapped_column(String(128))
    prompt_version: Mapped[str] = mapped_column(String(64))
    criteria_version: Mapped[int]

    # The deterministic pass, which runs before any model scoring and can
    # route to human review on its own.
    eligibility_outcome: Mapped[str] = mapped_column(String(16), index=True)
    rule_results: Mapped[dict] = mapped_column(JSONVariant)

    score: Mapped[int | None] = mapped_column(nullable=True)
    recommendation: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    # strengths, gaps, evidence, uncertainties — never sent to Frappe.
    payload: Mapped[dict] = mapped_column(JSONVariant, default=dict)

    # The scoring-safe projection actually handed to the model. Stored so the
    # data-minimization boundary is auditable rather than merely asserted.
    scoring_profile: Mapped[dict] = mapped_column(JSONVariant, default=dict)
