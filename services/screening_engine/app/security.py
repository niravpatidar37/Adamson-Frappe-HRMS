"""Request authentication between Frappe and the engine.

Both directions are signed with a shared secret. The engine sits on a private
network, but network position is not authentication: anything that reaches
that network could otherwise submit resumes or write scores, and a score feeds
a hiring decision.

The signature covers `timestamp + "." + raw body`. Signing the headers alone
would authenticate nothing about the payload.
"""

import hashlib
import hmac
import time

from fastapi import Header, HTTPException, Request, status

from app.config import get_settings

# Bounds replay of a captured request.
MAX_SKEW_SECONDS = 300


def sign(body: bytes, timestamp: str, secret: str) -> str:
    msg = timestamp.encode() + b"." + body
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()


def _unauthorized() -> HTTPException:
    # One indistinguishable failure for every cause: a caller must not learn
    # which part of the check it failed.
    return HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")


def _secret_for(key_id: str | None) -> str:
    """Resolve which shared secret a request is claiming to use.

    Rotation is why this exists: for the overlap both keys verify, so Frappe
    and the engine do not have to restart in the same instant.
    """
    settings = get_settings()
    if key_id is None or key_id == settings.callback_key_id:
        return settings.callback_secret
    if (
        settings.previous_callback_key_id
        and settings.previous_callback_secret
        and key_id == settings.previous_callback_key_id
    ):
        return settings.previous_callback_secret
    raise _unauthorized()


async def verify_signature(
    request: Request,
    # Optional at the framework level so a missing header is a 401 like every
    # other failure, rather than a 422 that tells a prober what was wrong.
    x_screening_timestamp: str | None = Header(default=None),
    x_screening_signature: str | None = Header(default=None),
    x_screening_key_id: str | None = Header(default=None),
) -> None:
    if not x_screening_timestamp or not x_screening_signature:
        raise _unauthorized()

    try:
        skew = abs(time.time() - float(x_screening_timestamp))
    except ValueError as exc:
        raise _unauthorized() from exc
    if skew > MAX_SKEW_SECONDS:
        raise _unauthorized()

    body = getattr(request.state, "raw_body", None)
    if body is None:
        # RawBodyMiddleware is not installed. Fail closed rather than fall
        # back to checking headers only, which authenticates nothing.
        raise _unauthorized()

    expected = sign(body, x_screening_timestamp, _secret_for(x_screening_key_id))
    if not hmac.compare_digest(expected, x_screening_signature):
        raise _unauthorized()
