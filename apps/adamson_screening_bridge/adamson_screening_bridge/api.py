"""Callback endpoint: the engine reports a finished scorecard.

`allow_guest=False` only proves *someone* is logged in. It does not prove the
caller is the engine, and combined with `ignore_permissions=True` that would
let any authenticated session write an arbitrary score to any applicant.
Scores feed hiring decisions, so the payload is signed and verified.
"""

import frappe

ALLOWED_RECOMMENDATIONS = {"strong_match", "review", "not_currently_shortlisted"}


@frappe.whitelist(allow_guest=False)
def record_scorecard():
    """Record a scorecard against a Job Applicant.

    TODO, all required before this is enabled:
      - verify the HMAC signature over the raw request body
      - check the receipt id against one this site actually dispatched
      - write as a dedicated service user instead of ignore_permissions

    Stores only score, recommendation and an evidence link. The parsed
    profile, excerpts and rule evidence stay in the engine — Frappe's
    tabVersion history would otherwise accumulate them on every update.
    """
    raise NotImplementedError("callback disabled until signature verification exists")
