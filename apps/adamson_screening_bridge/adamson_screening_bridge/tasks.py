"""Dispatch to the screening engine.

Nothing here parses, scores or imports an ML library. The bridge's whole job
is to hand work off and stay out of the way.

Configuration comes from site config, not from this module:

    bench --site <site> set-config screening_engine_url http://host.docker.internal:8100
    bench --site <site> set-config screening_callback_secret <the shared secret>
    bench --site <site> set-config screening_key_id v1
"""

import hashlib
import hmac
import time

import frappe
import requests

ENQUEUE_KWARGS = {
    "queue": "short",
    # Without this the job can start before the transaction that created the
    # applicant commits, and the worker finds no row.
    "enqueue_after_commit": True,
}

# Frappe's own view of the dispatch. A job already in one of these states has
# been handed over, so a re-run must not hand it over again — the engine is
# idempotent too, but two layers of it cost nothing and the second one saves a
# round trip.
ALREADY_HANDED_OVER = {"Queued", "Processing", "Scored"}

# The engine answers immediately by design: it writes a receipt and returns.
# Anything slower than this is a fault, not a slow parse.
REQUEST_TIMEOUT_SECONDS = 10


def dispatch_screening(doc, method=None):
    if not doc.get("resume_attachment"):
        return
    frappe.enqueue(
        "adamson_screening_bridge.tasks.send_to_engine",
        applicant=doc.name,
        **ENQUEUE_KWARGS,
    )


def _sign(body: bytes, timestamp: str, secret: str) -> str:
    """Must match app/security.py in the engine: timestamp + "." + raw body."""
    return hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()


def _load_resume(doc) -> tuple[bytes, str, str]:
    """Read the private file off disk.

    Deliberately not a URL handed to the engine. A URL would be either
    unauthenticated — candidate PII on an open endpoint — or would need engine
    credentials into Frappe.
    """
    rows = frappe.get_all(
        "File",
        filters={"file_url": doc.resume_attachment},
        fields=["name"],
        limit=1,
    )
    if not rows:
        raise FileNotFoundError(f"no File record for {doc.resume_attachment}")

    file_doc = frappe.get_doc("File", rows[0].name)
    with open(file_doc.get_full_path(), "rb") as handle:
        content = handle.read()

    filename = file_doc.file_name or "resume.pdf"
    content_type = "application/pdf"
    if filename.lower().endswith(".docx"):
        content_type = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    return content, filename, content_type


def _mark(applicant: str, values: dict) -> None:
    """Write without touching the document's version history.

    `doc.save()` would append to tabVersion on every status change. Keeping
    the engine's chatter out of that history is part of why the scorecard
    lives in the engine at all.
    """
    frappe.db.set_value("Job Applicant", applicant, values, update_modified=False)
    frappe.db.commit()


def send_to_engine(applicant: str) -> None:
    doc = frappe.get_doc("Job Applicant", applicant)
    if doc.get("custom_screening_status") in ALREADY_HANDED_OVER:
        return

    base_url = frappe.conf.get("screening_engine_url")
    secret = frappe.conf.get("screening_callback_secret")
    if not base_url or not secret:
        _mark(applicant, {"custom_screening_status": "Error",
                          "custom_screening_error": "screening engine is not configured"})
        return

    try:
        content, filename, content_type = _load_resume(doc)
    except Exception as exc:  # noqa: BLE001 - recorded, not swallowed
        frappe.log_error(title="screening: resume unreadable", message=str(exc))
        _mark(applicant, {"custom_screening_status": "Error",
                          "custom_screening_error": "resume file could not be read"})
        return

    checksum = hashlib.sha256(content).hexdigest()

    # Built by requests and then read back, rather than sent directly: the
    # signature covers the exact body, so the bytes have to be known before
    # they go out. requests picks a random multipart boundary.
    request = requests.Request(
        "POST",
        f"{base_url.rstrip('/')}/v1/screening/intake",
        data={"applicant_id": doc.name, "job_opening_id": doc.get("job_title") or ""},
        files={"resume": (filename, content, content_type)},
    ).prepare()

    timestamp = str(int(time.time()))
    request.headers.update(
        {
            "x-screening-timestamp": timestamp,
            "x-screening-signature": _sign(request.body, timestamp, secret),
            "x-screening-key-id": frappe.conf.get("screening_key_id") or "v1",
            # TODO: include the criteria version once Job Opening carries one.
            # Today a re-screen against new criteria would be suppressed as a
            # duplicate, which is wrong but not yet reachable.
            "Idempotency-Key": f"{doc.name}:{checksum}",
        }
    )

    try:
        response = requests.Session().send(request, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        # The message, never the request: it holds the resume bytes.
        frappe.log_error(title="screening: engine unreachable", message=str(exc))
        _mark(applicant, {"custom_screening_status": "Error",
                          "custom_screening_error": "screening engine unreachable"})
        return

    if response.status_code not in (200, 202):
        frappe.log_error(
            title="screening: engine rejected dispatch",
            message=f"{response.status_code} {response.text[:500]}",
        )
        _mark(applicant, {"custom_screening_status": "Error",
                          "custom_screening_error": f"engine returned {response.status_code}"})
        return

    # 200 means the engine already had this exact submission. That is a
    # success, not a conflict: the receipt it returns is the original.
    payload = response.json()
    _mark(
        applicant,
        {
            "custom_screening_status": "Queued",
            "custom_screening_tracking_id": payload.get("tracking_id") or payload.get("receipt_id"),
            "custom_screening_error": None,
        },
    )


def handle_requisition_closed(doc, method=None):
    """Cohort ranking runs when a requisition closes, not during intake.

    Ranking a moving population means a candidate's position changes as others
    apply, which is not something a recruiter can act on consistently.
    """
    raise NotImplementedError("cohort ranking not yet implemented")
