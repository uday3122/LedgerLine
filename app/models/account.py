
from datetime import datetime, timezone

from app import db


class Account(db.Model):
    __tablename__ = "accounts"

    id = db.Column(
        db.BigInteger,
        primary_key=True
    )

    account_number = db.Column(
        db.String(30),
        nullable=False,
        unique=True
    )

    account_name = db.Column(
        db.String(120),
        nullable=False
    )

    account_type = db.Column(
        db.String(20),
        nullable=False,
        default="CUSTOMER"
    )

    owner_user_id = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id"),
        nullable=True
    )

    balance_paise = db.Column(
        db.BigInteger,
        nullable=False,
        default=0
    )

    overdraft_enabled = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    overdraft_limit_paise = db.Column(
        db.BigInteger,
        nullable=False,
        default=0
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    owner = db.relationship(
        "User",
        backref="accounts",
        lazy=True
    )

    def __repr__(self):
        return f"<Account {self.account_number}>"
