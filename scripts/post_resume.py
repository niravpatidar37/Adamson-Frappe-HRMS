#!/usr/bin/env python3
"""Submit a resume to the screening engine, signed the way Frappe will sign it.

Standard library only, so it runs with any Python on the host without an
environment. curl cannot do this on its own: the signature covers the exact
multipart body, so the body has to be built before it is sent.

    python scripts/post_resume.py cv.pdf --applicant HR-APP-0001 --job HR-OPN-0001
    python scripts/post_resume.py --receipt <uuid>          # read one back
"""

import argparse
import hashlib
import hmac
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

BOUNDARY = f"----adamson{uuid.uuid4().hex}"


def sign(body: bytes, timestamp: str, secret: str) -> str:
    return hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()


def build_multipart(applicant_id: str, job_opening_id: str, path: Path) -> bytes:
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    parts = []
    for name, value in (("applicant_id", applicant_id), ("job_opening_id", job_opening_id)):
        parts.append(
            f"--{BOUNDARY}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        )
    parts.append(
        f"--{BOUNDARY}\r\n"
        f'Content-Disposition: form-data; name="resume"; filename="{path.name}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n".encode()
        + path.read_bytes()
        + b"\r\n"
    )
    parts.append(f"--{BOUNDARY}--\r\n".encode())
    return b"".join(parts)


def send(request: urllib.request.Request) -> int:
    """Status to stderr, body to stdout.

    Keeping stdout pure JSON means the caller can pipe it straight into
    `ConvertFrom-Json` or `jq` without stripping a status line first.
    """
    try:
        with urllib.request.urlopen(request) as response:
            print(f"HTTP {response.status}", file=sys.stderr)
            print(json.dumps(json.loads(response.read()), indent=2))
            return 0
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}", exc.read().decode(errors="replace"), file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("resume", nargs="?", type=Path)
    parser.add_argument("--applicant", default="HR-APP-2026-00001")
    parser.add_argument("--job", default="HR-OPN-2026-00001")
    parser.add_argument("--receipt", help="read a receipt back instead of posting")
    parser.add_argument("--base-url", default=os.environ.get("ENGINE_URL", "http://127.0.0.1:8100"))
    parser.add_argument(
        "--secret",
        default=os.environ.get("SCREENING_CALLBACK_SECRET"),
        help="defaults to $SCREENING_CALLBACK_SECRET",
    )
    args = parser.parse_args()

    if not args.secret:
        parser.error("no secret: pass --secret or set SCREENING_CALLBACK_SECRET")

    timestamp = str(int(time.time()))

    if args.receipt:
        headers = {
            "x-screening-timestamp": timestamp,
            "x-screening-signature": sign(b"", timestamp, args.secret),
        }
        url = f"{args.base_url}/v1/scorecards/{args.receipt}"
        return send(urllib.request.Request(url, headers=headers, method="GET"))

    if args.resume is None:
        parser.error("pass a resume file, or --receipt to read one back")
    if not args.resume.is_file():
        parser.error(f"no such file: {args.resume}")

    body = build_multipart(args.applicant, args.job, args.resume)
    headers = {
        "content-type": f"multipart/form-data; boundary={BOUNDARY}",
        "x-screening-timestamp": timestamp,
        "x-screening-signature": sign(body, timestamp, args.secret),
    }
    url = f"{args.base_url}/v1/screening/intake"
    return send(urllib.request.Request(url, data=body, headers=headers, method="POST"))


if __name__ == "__main__":
    raise SystemExit(main())
