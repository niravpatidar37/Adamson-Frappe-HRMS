"""SQLAlchemy base and shared column types."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Postgres stores `json` as text and reparses on every read; `jsonb` is binary
# and indexable. The variant keeps SQLite usable for tests.
JSONVariant = JSON().with_variant(JSONB, "postgresql")


class Base(DeclarativeBase):
    pass


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
