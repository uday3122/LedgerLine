
from datetime import datetime, timezone

from app import db


class IdempotencyKey(db.Model):
    __tablename__ = "idempotency_keys"

    id = db.Column(
        db.BigInteger,
        primary_key=True
    )

    user_id = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id"),
        nullable=False
    )

    idempotency_key = db.Column(
        db.String(150),
        nullable=False
    )

    request_hash = db.Column(
        db.String(64),
        nullable=False
    )

    transaction_id = db.Column(
        db.BigInteger,
        db.ForeignKey("ledger_transactions.id"),
        nullable=True
    )

    response_data = db.Column(
        db.JSON,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "idempotency_key",
            name="uq_user_idempotency_key"
        ),
    )
