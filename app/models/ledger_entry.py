
from datetime import datetime, timezone

from app import db


class LedgerEntry(db.Model):
    __tablename__ = "ledger_entries"

    id = db.Column(
        db.BigInteger,
        primary_key=True
    )

    transaction_id = db.Column(
        db.BigInteger,
        db.ForeignKey("ledger_transactions.id"),
        nullable=False
    )

    account_id = db.Column(
        db.BigInteger,
        db.ForeignKey("accounts.id"),
        nullable=False
    )

    entry_side = db.Column(
        db.String(10),
        nullable=False
    )

    amount_paise = db.Column(
        db.BigInteger,
        nullable=False
    )

    resulting_balance_paise = db.Column(
        db.BigInteger,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    account = db.relationship(
        "Account",
        backref="ledger_entries"
    )

    def __repr__(self):
        return f"<LedgerEntry {self.id}: {self.entry_side}>"
