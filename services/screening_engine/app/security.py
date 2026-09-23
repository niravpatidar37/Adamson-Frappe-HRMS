"""Request authentication between Frappe and the engine.

Both directions are signed with a shared secret. The engine is on a private
network, but network position is not authentication: anything that can reach
the internal network could otherwise submit resumes or write scores, and a
score feeds a hiring decision.
"""

import hashlib
import hmac
import time

from fastapi import Header, HTTPException, status

# Bounds replay of a captured request.
MAX_SKEW_SECONDS = 300


def sign(body: bytes, timestamp: str, secret: str) -> str:
    msg = timestamp.encode() + b"." + body
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()


async def verify_signature(
    x_screening_timestamp: str = Header(...),
    x_screening_signature: str = Header(...),
) -> None:
    try:
        skew = abs(time.time() - float(x_screening_timestamp))
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized") from exc
    if skew > MAX_SKEW_SECONDS:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")

    # TODO: read the secret via get_settings() and verify. The signature is
    # computed over the raw body, which needs middleware to
    # capture before FastAPI parses the multipart form. Header checks alone do
    # not authenticate the payload — finish this before anything real is wired.
    if not x_screening_signature:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
