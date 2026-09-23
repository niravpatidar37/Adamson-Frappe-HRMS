"""receipt idempotency key

A retried dispatch must not become a second screening of the same document.
The constraint is in the database rather than in a check-then-insert, because
two concurrent retries would both pass a check.

Revision ID: 0002_receipt_idempotency_key
Revises: 0001_initial_audit_ledger
Create Date: 2026-09-23
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_receipt_idempotency_key"
down_revision = "0001_initial_audit_ledger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing rows predate the key and have nothing meaningful to hold, so
    # the column is added nullable, backfilled from the id (unique by
    # construction), and only then made NOT NULL.
    op.add_column(
        "screening_receipts", sa.Column("idempotency_key", sa.String(length=255), nullable=True)
    )
    # CAST rather than `|| id`: on Postgres the column is uuid, which will
    # not concatenate with text, and `::text` is not valid on SQLite.
    op.execute(
        "UPDATE screening_receipts "
        "SET idempotency_key = 'legacy:' || CAST(id AS VARCHAR(64))"
    )
    op.alter_column("screening_receipts", "idempotency_key", nullable=False)
    op.create_index(
        op.f("ix_screening_receipts_idempotency_key"),
        "screening_receipts",
        ["idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_screening_receipts_idempotency_key"), table_name="screening_receipts")
    op.drop_column("screening_receipts", "idempotency_key")
