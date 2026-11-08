
from datetime import datetime, timezone

from app import db


class OperationAttempt(db.Model):
    __tablename__ = "operation_attempts"

    id = db.Column(
        db.BigInteger,
        primary_key=True
    )

    user_id = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id"),
        nullable=True
    )

    account_id = db.Column(
        db.BigInteger,
        db.ForeignKey("accounts.id"),
        nullable=True
    )

    operation_type = db.Column(
        db.String(30),
        nullable=False
    )

    amount_paise = db.Column(
        db.BigInteger,
        nullable=True
    )

    outcome = db.Column(
        db.String(20),
        nullable=False
    )

    reason = db.Column(
        db.Text,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
