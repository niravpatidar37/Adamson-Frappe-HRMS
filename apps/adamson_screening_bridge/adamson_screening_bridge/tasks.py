"""Dispatch to the screening engine.

Nothing here parses, scores or imports an ML library. The bridge's whole job
is to hand work off and stay out of the way.
"""

import frappe

ENQUEUE_KWARGS = {
    "queue": "short",
    # Without this the job can start before the transaction that created the
    # applicant commits, and the worker finds no row.
    "enqueue_after_commit": True,
}


def dispatch_screening(doc, method=None):
    if not doc.resume_attachment:
        return
    frappe.enqueue(
        "adamson_screening_bridge.tasks.send_to_engine",
        applicant=doc.name,
        **ENQUEUE_KWARGS,
    )


def send_to_engine(applicant: str) -> None:
    """Push the resume bytes to the engine and mark the applicant in progress.

    The file is POSTed rather than linked. A link would be either
    unauthenticated — candidate PII on an open URL — or would require giving
    the engine credentials into Frappe. Neither is acceptable.

    TODO: sign the request with the shared secret (see engine app/security.py)
    and read the engine URL from site config rather than hardcoding it.
    """
    raise NotImplementedError("blocked on the transport decision in the spike")


def handle_requisition_closed(doc, method=None):
    """Cohort ranking runs when a requisition closes, not during intake.

    Ranking a moving population means a candidate's position changes as others
    apply, which is not something a recruiter can act on consistently.
    """
    raise NotImplementedError("cohort ranking not yet implemented")
