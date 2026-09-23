"""Raw-body capture.

The HMAC signature covers the request body, so the bytes have to be captured
before FastAPI parses the multipart form: once the ASGI receive channel is
drained the body cannot be read back. A dependency is too late — FastAPI
parses the body before it solves dependencies — so this is pure ASGI
middleware that buffers the body and replays it downstream.

It also enforces the byte ceiling. Buffering has to happen for the signature
to be checkable at all, so the ceiling belongs here rather than deeper in.
"""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Multipart framing, headers and the form fields wrapped around the file.
# The file itself is bounded separately by settings.max_upload_bytes.
_ENVELOPE_SLACK = 1024 * 1024


class RawBodyMiddleware:
    def __init__(self, app: ASGIApp, max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes + _ENVELOPE_SLACK

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        chunks: list[bytes] = []
        total = 0
        more_body = True
        while more_body:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            total += len(chunk)
            if total > self.max_body_bytes:
                await _reject_too_large(send)
                return
            chunks.append(chunk)
            more_body = bool(message.get("more_body", False))

        body = b"".join(chunks)
        scope.setdefault("state", {})["raw_body"] = body

        replayed = False

        async def replay() -> Message:
            nonlocal replayed
            if replayed:
                return {"type": "http.disconnect"}
            replayed = True
            return {"type": "http.request", "body": body, "more_body": False}

        await self.app(scope, replay, send)


async def _reject_too_large(send: Send) -> None:
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [(b"content-type", b"application/json")],
        }
    )
    await send({"type": "http.response.body", "body": b'{"detail":"request too large"}'})
