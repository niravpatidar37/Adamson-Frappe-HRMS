"""Read-only access to completed scorecards.

Frappe stores a score, a recommendation and a link. The evidence behind them
lives here, so a recruiter following that link lands on this service. Keeping
it here is what stops the parsed profile and its excerpts entering Frappe's
database and its tabVersion history.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.security import verify_signature

router = APIRouter()


@router.get("/{receipt_id}")
async def get_scorecard(receipt_id: str, _: None = Depends(verify_signature)) -> dict:
    # TODO: read from the audit ledger once the worker writes to it.
    raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
