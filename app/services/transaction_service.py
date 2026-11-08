
import uuid
import hashlib
import json

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app import db
from app.models import (
    Account,
    LedgerTransaction,
    LedgerEntry,
    IdempotencyKey,
)


class TransactionError(Exception):
    pass


# =====================================================
# VALIDATION
# =====================================================

def _validate_amount(amount_paise):
    if not isinstance(amount_paise, int) or isinstance(amount_paise, bool):
        raise TransactionError(
            "Amount must be an integer number of paise"
        )

    if amount_paise <= 0:
        raise TransactionError("Amount must be greater than zero")


def _validate_idempotency_key(idempotency_key):
    if (
        not isinstance(idempotency_key, str)
        or not idempotency_key.strip()
        or len(idempotency_key) > 128
    ):
        raise TransactionError("A valid idempotency key is required")

    return idempotency_key.strip()


def _request_hash(request_data):
    return hashlib.sha256(
        json.dumps(
            request_data,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


# =====================================================
# IDEMPOTENCY KEY RESERVATION
# =====================================================

def _reserve_idempotency_key(
    initiated_by,
    idempotency_key,
    request_hash,
):
    reservation = (
        insert(IdempotencyKey)
        .values(
            user_id=initiated_by,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        .on_conflict_do_nothing(
            index_elements=[
                IdempotencyKey.user_id,
                IdempotencyKey.idempotency_key,
            ]
        )
        .returning(IdempotencyKey.id)
    )

    inserted_id = db.session.execute(
        reservation
    ).scalar_one_or_none()

    # New idempotency key successfully inserted.
    if inserted_id is not None:
        return None

    # Existing key: retrieve the original request.
    existing = db.session.execute(
        select(IdempotencyKey)
        .where(
            IdempotencyKey.user_id == initiated_by,
            IdempotencyKey.idempotency_key == idempotency_key,
        )
        .with_for_update()
    ).scalar_one()

    # Same key cannot be reused for a different request.
    if existing.request_hash != request_hash:
        raise TransactionError(
            "Idempotency key was already used for a different request"
        )

    # Return the original completed response.
    if (
        existing.transaction_id is not None
        and existing.response_data is not None
    ):
        result = existing.response_data
        db.session.rollback()
        return result

    raise TransactionError(
        "The original request has no completed result"
    )


# =====================================================
# SAVE IDEMPOTENCY RESULT
# =====================================================

def _save_idempotency_result(
    initiated_by,
    idempotency_key,
    transaction_id,
    result,
):
    key_record = db.session.execute(
        select(IdempotencyKey)
        .where(
            IdempotencyKey.user_id == initiated_by,
            IdempotencyKey.idempotency_key == idempotency_key,
        )
        .with_for_update()
    ).scalar_one()

    key_record.transaction_id = transaction_id
    key_record.response_data = result


# =====================================================
# INTERNAL MONEY TRANSFER
# =====================================================

def move_money(
    transaction_type,
    source_account_id,
    destination_account_id,
    amount_paise,
    initiated_by,
    idempotency_key,
    description=None,
):
    _validate_amount(amount_paise)

    if source_account_id == destination_account_id:
        raise TransactionError("Source and destination must differ")

    if transaction_type != "TRANSFER":
        raise TransactionError("Unsupported transaction type")

    idempotency_key = _validate_idempotency_key(idempotency_key)
    description = description or "Internal transfer"

    request_data = {
        "transaction_type": transaction_type,
        "source_account_id": source_account_id,
        "destination_account_id": destination_account_id,
        "amount_paise": amount_paise,
        "description": description,
    }

    request_hash = _request_hash(request_data)

    try:
        replay_result = _reserve_idempotency_key(
            initiated_by,
            idempotency_key,
            request_hash,
        )

        if replay_result is not None:
            return replay_result

        # Lock accounts in deterministic order.
        account_ids = sorted([
            source_account_id,
            destination_account_id,
        ])

        accounts = db.session.execute(
            select(Account)
            .where(Account.id.in_(account_ids))
            .order_by(Account.id)
            .with_for_update()
        ).scalars().all()

        if len(accounts) != 2:
            raise TransactionError("Account not found")

        account_map = {
            account.id: account for account in accounts
        }

        source = account_map[source_account_id]
        destination = account_map[destination_account_id]

        if not source.is_active or not destination.is_active:
            raise TransactionError("Inactive account")

        if (
            source.account_type != "CUSTOMER"
            or destination.account_type != "CUSTOMER"
        ):
            raise TransactionError(
                "Transfers require customer accounts"
            )

        available_balance = source.balance_paise

        if source.overdraft_enabled:
            available_balance += source.overdraft_limit_paise

        if available_balance < amount_paise:
            raise TransactionError("Insufficient funds")

        # Update account balances.
        source.balance_paise -= amount_paise
        destination.balance_paise += amount_paise

        # Create transaction.
        transaction = LedgerTransaction(
            transaction_reference=uuid.uuid4(),
            transaction_type="TRANSFER",
            status="POSTED",
            amount_paise=amount_paise,
            description=description,
            initiated_by=initiated_by,
        )

        db.session.add(transaction)
        db.session.flush()

        # Double-entry ledger.
        db.session.add_all([
            LedgerEntry(
                transaction_id=transaction.id,
                account_id=source.id,
                entry_side="DEBIT",
                amount_paise=amount_paise,
                resulting_balance_paise=source.balance_paise,
            ),
            LedgerEntry(
                transaction_id=transaction.id,
                account_id=destination.id,
                entry_side="CREDIT",
                amount_paise=amount_paise,
                resulting_balance_paise=destination.balance_paise,
            ),
        ])

        result = {
            "transaction_id": transaction.id,
            "reference": str(transaction.transaction_reference),
            "amount_paise": amount_paise,
            "status": "POSTED",
        }

        _save_idempotency_result(
            initiated_by,
            idempotency_key,
            transaction.id,
            result,
        )

        db.session.commit()
        return result

    except Exception:
        db.session.rollback()
        raise


# =====================================================
# DEPOSIT AND WITHDRAWAL
# =====================================================

def _post_external_money(
    transaction_type,
    account_id,
    amount_paise,
    initiated_by,
    idempotency_key,
    description=None,
):
    _validate_amount(amount_paise)

    if transaction_type not in ("DEPOSIT", "WITHDRAWAL"):
        raise TransactionError(
            "Invalid external transaction type"
        )

    idempotency_key = _validate_idempotency_key(idempotency_key)
    description = description or transaction_type.title()

    request_data = {
        "transaction_type": transaction_type,
        "account_id": account_id,
        "amount_paise": amount_paise,
        "description": description,
    }

    request_hash = _request_hash(request_data)

    try:
        replay_result = _reserve_idempotency_key(
            initiated_by,
            idempotency_key,
            request_hash,
        )

        if replay_result is not None:
            return replay_result

        # Find the system clearing account.
        system_account = db.session.execute(
            select(Account).where(
                Account.account_number == "SYSTEM-CLEARING-001"
            )
        ).scalar_one_or_none()

        if system_account is None or not system_account.is_active:
            raise TransactionError(
                "System clearing account unavailable"
            )

        # Lock customer and system accounts in ID order.
        account_ids = sorted([
            account_id,
            system_account.id,
        ])

        accounts = db.session.execute(
            select(Account)
            .where(Account.id.in_(account_ids))
            .order_by(Account.id)
            .with_for_update()
        ).scalars().all()

        if len(accounts) != 2:
            raise TransactionError("Account not found")

        account_map = {
            account.id: account for account in accounts
        }

        customer = account_map[account_id]
        system = account_map[system_account.id]

        if (
            not customer.is_active
            or customer.account_type != "CUSTOMER"
        ):
            raise TransactionError("Invalid customer account")

        if (
            not system.is_active
            or system.account_type != "SYSTEM"
        ):
            raise TransactionError("Invalid system account")

        # Apply deposit or withdrawal.
        if transaction_type == "DEPOSIT":

            customer.balance_paise += amount_paise
            system.balance_paise -= amount_paise

            customer_side = "CREDIT"
            system_side = "DEBIT"

        else:

            available_balance = customer.balance_paise

            if customer.overdraft_enabled:
                available_balance += customer.overdraft_limit_paise

            if available_balance < amount_paise:
                raise TransactionError("Insufficient funds")

            customer.balance_paise -= amount_paise
            system.balance_paise += amount_paise

            customer_side = "DEBIT"
            system_side = "CREDIT"

        # Create transaction record.
        transaction = LedgerTransaction(
            transaction_reference=uuid.uuid4(),
            transaction_type=transaction_type,
            status="POSTED",
            amount_paise=amount_paise,
            description=description,
            initiated_by=initiated_by,
        )

        db.session.add(transaction)
        db.session.flush()

        # Create double-entry ledger records.
        db.session.add_all([
            LedgerEntry(
                transaction_id=transaction.id,
                account_id=customer.id,
                entry_side=customer_side,
                amount_paise=amount_paise,
                resulting_balance_paise=customer.balance_paise,
            ),
            LedgerEntry(
                transaction_id=transaction.id,
                account_id=system.id,
                entry_side=system_side,
                amount_paise=amount_paise,
                resulting_balance_paise=system.balance_paise,
            ),
        ])

        result = {
            "transaction_id": transaction.id,
            "reference": str(transaction.transaction_reference),
            "transaction_type": transaction_type,
            "account_id": customer.id,
            "amount_paise": amount_paise,
            "status": "POSTED",
        }

        _save_idempotency_result(
            initiated_by,
            idempotency_key,
            transaction.id,
            result,
        )

        db.session.commit()
        return result

    except Exception:
        db.session.rollback()
        raise


# =====================================================
# DEPOSIT FUNCTION
# =====================================================

def deposit_money(
    account_id,
    amount_paise,
    initiated_by,
    idempotency_key,
    description=None,
):
    return _post_external_money(
        transaction_type="DEPOSIT",
        account_id=account_id,
        amount_paise=amount_paise,
        initiated_by=initiated_by,
        idempotency_key=idempotency_key,
        description=description,
    )


# =====================================================
# WITHDRAWAL FUNCTION
# =====================================================

def withdraw_money(
    account_id,
    amount_paise,
    initiated_by,
    idempotency_key,
    description=None,
):
    return _post_external_money(
        transaction_type="WITHDRAWAL",
        account_id=account_id,
        amount_paise=amount_paise,
        initiated_by=initiated_by,
        idempotency_key=idempotency_key,
        description=description,
    )
