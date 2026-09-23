"""Quarantine storage for uploaded resumes.

Bytes land here before anything parses them; the worker reads from here, and
a scanner would too. Nothing serves these files over HTTP.

The path is built from attacker-controlled input (the upload filename), so it
is sanitised and then the resolved path is checked against the root. Both
steps are needed — sanitising alone has been wrong before.
"""

import re
import uuid
from pathlib import Path

from screening.core.exceptions import UntrustedContentError

_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]")
_MAX_FILENAME_LENGTH = 128


def safe_filename(filename: str) -> str:
    """`Path(filename).name` is NOT sufficient here. On POSIX a backslash is
    an ordinary filename character, so `Path("..\\..\\evil.pdf").name` returns
    the whole string unchanged."""
    base = filename.replace("\\", "/").rsplit("/", 1)[-1]
    base = _UNSAFE_CHARS.sub("_", base).lstrip(".")
    return base[:_MAX_FILENAME_LENGTH] or "resume"


def save_quarantined(*, root: Path, receipt_id: uuid.UUID, filename: str, data: bytes) -> str:
    """Write the bytes and return the object key, relative to the root."""
    object_key = f"{receipt_id}/{safe_filename(filename)}"
    resolved_root = root.resolve()
    path = (resolved_root / object_key).resolve()
    if not path.is_relative_to(resolved_root):
        raise UntrustedContentError("resolved storage path escapes the quarantine root")
    path.parent.mkdir(parents=True, exist_ok=True)
    # "xb": a receipt id is used once, so a collision means something is wrong.
    with open(path, "xb") as handle:
        handle.write(data)
    return object_key


def quarantined_path(*, root: Path, object_key: str) -> Path:
    """Resolve a stored key back to a path, re-checking containment. The key
    comes out of the database, and a database is not a trust boundary."""
    resolved_root = root.resolve()
    path = (resolved_root / object_key).resolve()
    if not path.is_relative_to(resolved_root):
        raise UntrustedContentError("object key escapes the quarantine root")
    return path
