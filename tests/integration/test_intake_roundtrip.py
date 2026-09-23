"""End-to-end: a signed resume becomes a receipt, an unsigned one does not."""

import time
import uuid
from pathlib import Path

import pytest

from app.security import sign

BOUNDARY = "boundary-for-a-deterministic-body"
PDF_BYTES = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\ntrailer\n%%EOF\n"


def build_multipart(
    *,
    applicant_id: str,
    job_opening_id: str,
    filename: str,
    content_type: str,
    data: bytes,
) -> bytes:
    """Built by hand, not by httpx.

    The signature covers the exact request body, so the test has to know what
    those bytes are. httpx picks a random boundary and would end up signing
    something other than what it sends.
    """
    parts = []
    for name, value in (("applicant_id", applicant_id), ("job_opening_id", job_opening_id)):
        parts.append(
            f"--{BOUNDARY}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        )
    parts.append(
        f"--{BOUNDARY}\r\n"
        f'Content-Disposition: form-data; name="resume"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n".encode()
        + data
        + b"\r\n"
    )
    parts.append(f"--{BOUNDARY}--\r\n".encode())
    return b"".join(parts)


def signed_headers(body: bytes, secret: str, timestamp: str | None = None) -> dict[str, str]:
    timestamp = timestamp or str(int(time.time()))
    return {
        "x-screening-timestamp": timestamp,
        "x-screening-signature": sign(body, timestamp, secret),
    }


def post_intake(client, body: bytes, headers: dict[str, str]):
    return client.post(
        "/v1/screening/intake",
        content=body,
        headers={"content-type": f"multipart/form-data; boundary={BOUNDARY}", **headers},
    )


def read_receipt(receipt_id: str):
    from app.db.models import ScreeningReceipt
    from app.db.session import get_session_factory

    with get_session_factory()() as session:
        return session.get(ScreeningReceipt, uuid.UUID(receipt_id))


@pytest.fixture
def valid_body() -> bytes:
    return build_multipart(
        applicant_id="HR-APP-2026-00042",
        job_opening_id="HR-OPN-2026-00007",
        filename="cv.pdf",
        content_type="application/pdf",
        data=PDF_BYTES,
    )


def test_a_signed_upload_is_accepted_and_persisted(client, secret, quarantine_root, valid_body):
    response = post_intake(client, valid_body, signed_headers(valid_body, secret))
    assert response.status_code == 202, response.text

    payload = response.json()
    receipt = read_receipt(payload["receipt_id"])
    assert receipt is not None
    assert receipt.applicant_id == "HR-APP-2026-00042"
    assert receipt.job_opening_id == "HR-OPN-2026-00007"
    assert receipt.status == "accepted"
    assert receipt.checksum_sha256 == payload["checksum_sha256"]
    assert (Path(quarantine_root) / receipt.object_key).read_bytes() == PDF_BYTES


def test_an_unsigned_upload_is_rejected(client, valid_body):
    # 401 and not 422: a missing header must not be distinguishable from a
    # wrong one.
    assert post_intake(client, valid_body, {}).status_code == 401


def test_a_wrong_secret_is_rejected(client, valid_body):
    headers = signed_headers(valid_body, "a-different-secret-of-sufficient-len")
    assert post_intake(client, valid_body, headers).status_code == 401


def test_a_tampered_body_is_rejected(client, secret, valid_body):
    """The whole reason the signature covers the body and not just the headers."""
    headers = signed_headers(valid_body, secret)
    tampered = build_multipart(
        applicant_id="HR-APP-2026-99999",
        job_opening_id="HR-OPN-2026-00007",
        filename="cv.pdf",
        content_type="application/pdf",
        data=PDF_BYTES,
    )
    assert post_intake(client, tampered, headers).status_code == 401


def test_a_stale_timestamp_is_rejected(client, secret, valid_body):
    headers = signed_headers(valid_body, secret, timestamp=str(int(time.time()) - 3600))
    assert post_intake(client, valid_body, headers).status_code == 401


def test_a_file_whose_bytes_are_not_a_pdf_is_rejected(client, secret):
    body = build_multipart(
        applicant_id="HR-APP-2026-00043",
        job_opening_id="HR-OPN-2026-00007",
        filename="cv.pdf",
        content_type="application/pdf",
        data=b"GIF89a this is not a pdf",
    )
    assert post_intake(client, body, signed_headers(body, secret)).status_code == 400


def test_a_traversing_filename_stays_inside_the_quarantine_root(client, secret, quarantine_root):
    body = build_multipart(
        applicant_id="HR-APP-2026-00044",
        job_opening_id="HR-OPN-2026-00007",
        filename="..\\..\\..\\etc\\passwd.pdf",
        content_type="application/pdf",
        data=PDF_BYTES,
    )
    response = post_intake(client, body, signed_headers(body, secret))
    assert response.status_code == 202, response.text

    receipt = read_receipt(response.json()["receipt_id"])
    assert receipt is not None
    assert ".." not in receipt.object_key
    root = Path(quarantine_root).resolve()
    assert (root / receipt.object_key).resolve().is_relative_to(root)


def test_a_receipt_can_be_read_back_before_it_has_a_scorecard(client, secret, valid_body):
    created = post_intake(client, valid_body, signed_headers(valid_body, secret))
    receipt_id = created.json()["receipt_id"]

    response = client.get(f"/v1/scorecards/{receipt_id}", headers=signed_headers(b"", secret))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "accepted"
    assert body["scorecard"] is None


def test_an_unknown_receipt_is_a_404_not_a_500(client, secret):
    response = client.get(f"/v1/scorecards/{uuid.uuid4()}", headers=signed_headers(b"", secret))
    assert response.status_code == 404


def count_receipts_for(applicant_id: str) -> int:
    from sqlalchemy import func, select

    from app.db.models import ScreeningReceipt
    from app.db.session import get_session_factory

    with get_session_factory()() as session:
        return session.scalar(
            select(func.count())
            .select_from(ScreeningReceipt)
            .where(ScreeningReceipt.applicant_id == applicant_id)
        )


def test_the_same_resume_twice_yields_one_receipt(client, secret):
    """Frappe cannot tell a timeout from a failure, so it retries. A retry
    must not become a second screening of the same person."""
    body = build_multipart(
        applicant_id="HR-APP-2026-IDEM-1",
        job_opening_id="HR-OPN-2026-00007",
        filename="cv.pdf",
        content_type="application/pdf",
        data=PDF_BYTES,
    )
    first = post_intake(client, body, signed_headers(body, secret))
    assert first.status_code == 202, first.text
    assert first.json()["idempotent_replay"] is False

    second = post_intake(client, body, signed_headers(body, secret))
    assert second.status_code == 200, second.text
    assert second.json()["idempotent_replay"] is True
    assert second.json()["receipt_id"] == first.json()["receipt_id"]

    assert count_receipts_for("HR-APP-2026-IDEM-1") == 1


def test_an_explicit_idempotency_key_is_honoured(client, secret):
    def body_for(filename: str) -> bytes:
        return build_multipart(
            applicant_id="HR-APP-2026-IDEM-2",
            job_opening_id="HR-OPN-2026-00007",
            filename=filename,
            content_type="application/pdf",
            data=PDF_BYTES,
        )

    key = {"idempotency-key": "HR-APP-2026-IDEM-2:blueprint-3"}
    first_body = body_for("cv.pdf")
    first = post_intake(client, first_body, {**signed_headers(first_body, secret), **key})
    assert first.status_code == 202, first.text

    # A different filename, so the derived key would differ. The explicit key
    # is what decides.
    second_body = body_for("cv-renamed.pdf")
    second = post_intake(client, second_body, {**signed_headers(second_body, secret), **key})
    assert second.status_code == 200, second.text
    assert second.json()["receipt_id"] == first.json()["receipt_id"]
    assert count_receipts_for("HR-APP-2026-IDEM-2") == 1


def test_the_same_file_from_a_different_applicant_is_a_separate_receipt(client, secret):
    """Two people may legitimately submit byte-identical documents."""
    for applicant in ("HR-APP-2026-IDEM-3", "HR-APP-2026-IDEM-4"):
        body = build_multipart(
            applicant_id=applicant,
            job_opening_id="HR-OPN-2026-00007",
            filename="cv.pdf",
            content_type="application/pdf",
            data=PDF_BYTES,
        )
        assert post_intake(client, body, signed_headers(body, secret)).status_code == 202

    assert count_receipts_for("HR-APP-2026-IDEM-3") == 1
    assert count_receipts_for("HR-APP-2026-IDEM-4") == 1


def test_a_request_naming_an_unknown_key_id_is_rejected(client, secret, valid_body):
    headers = signed_headers(valid_body, secret) | {"x-screening-key-id": "v99"}
    assert post_intake(client, valid_body, headers).status_code == 401


def test_a_request_naming_the_current_key_id_is_accepted(client, secret):
    body = build_multipart(
        applicant_id="HR-APP-2026-KEYID",
        job_opening_id="HR-OPN-2026-00007",
        filename="cv.pdf",
        content_type="application/pdf",
        data=PDF_BYTES,
    )
    headers = signed_headers(body, secret) | {"x-screening-key-id": "v1"}
    assert post_intake(client, body, headers).status_code == 202
