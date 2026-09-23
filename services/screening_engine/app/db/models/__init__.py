"""Audit ledger models.

Deliberately small. Frappe is the system of record for jobs, applicants and
their lifecycle; this database holds only what Frappe must not — the parsed
profile, the evidence, and an immutable record of what was decided and why.
"""

from app.db.models.scorecard_audit import ScorecardAudit, ScreeningReceipt  # noqa: F401
