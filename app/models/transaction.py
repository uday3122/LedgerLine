
from datetime import datetime, timezone
import uuid

from app import db


class LedgerTransaction(db.Model):
    __tablename__ = "ledger_transactions"

    id = db.Column(
        db.BigInteger,
        primary_key=True
    )

    transaction_reference = db.Column(
        db.Uuid(as_uuid=True),
        nullable=False,
        unique=True,
        default=uuid.uuid4
    )

    transaction_type = db.Column(
        db.String(20),
        nullable=False
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="POSTED"
    )

    amount_paise = db.Column(
        db.BigInteger,
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    initiated_by = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id"),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    initiator = db.relationship(
        "User",
        backref="transactions"
    )

    entries = db.relationship(
        "LedgerEntry",
        backref="transaction",
        lazy=True
    )

    def __repr__(self):
        return f"<LedgerTransaction {self.transaction_reference}>"
