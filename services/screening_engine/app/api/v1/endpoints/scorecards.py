"""Read-only access to receipts and completed scorecards.

Frappe stores a score, a recommendation and a link. The evidence behind them
lives here, so a recruiter following that link lands on this service. Keeping
it here is what stops the parsed profile and its excerpts entering Frappe's
database and its tabVersion history.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ScorecardAudit, ScreeningReceipt
from app.db.session import get_db
from app.security import verify_signature

router = APIRouter()


@router.get("/{receipt_id}")
async def get_scorecard(
    receipt_id: str,
    _: None = Depends(verify_signature),
    db: Session = Depends(get_db),
) -> dict:
    try:
        key = uuid.UUID(receipt_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found") from exc

    receipt = db.get(ScreeningReceipt, key)
    if receipt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")

    # Re-screening appends rather than updates, so the newest row is current
    # and the older ones stay readable as the decisions they were.
    audit = db.scalars(
        select(ScorecardAudit)
        .where(ScorecardAudit.receipt_id == key)
        .order_by(ScorecardAudit.created_at.desc())
        .limit(1)
    ).first()

    body: dict = {
        "receipt_id": str(receipt.id),
        "applicant_id": receipt.applicant_id,
        "job_opening_id": receipt.job_opening_id,
        "status": receipt.status,
        "created_at": receipt.created_at.isoformat() if receipt.created_at else None,
        "completed_at": receipt.completed_at.isoformat() if receipt.completed_at else None,
        "error_message": receipt.error_message,
        "scorecard": None,
    }
    if audit is not None:
        body["scorecard"] = {
            "audit_id": str(audit.id),
            "model_id": audit.model_id,
            "prompt_version": audit.prompt_version,
            "criteria_version": audit.criteria_version,
            "eligibility_outcome": audit.eligibility_outcome,
            "rule_results": audit.rule_results,
            "score": audit.score,
            "recommendation": audit.recommendation,
            "evidence": audit.payload,
            "scoring_profile": audit.scoring_profile,
        }
    return body
