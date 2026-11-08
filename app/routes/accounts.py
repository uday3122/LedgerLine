
import uuid

from flask import Blueprint, request, jsonify, g
from sqlalchemy import select, desc
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import (
    Account,
    User,
    LedgerEntry,
    LedgerTransaction,
    OperationAttempt,
)
from app.utils.auth_helpers import (
    current_user_required,
    roles_required,
)


accounts_bp = Blueprint(
    "accounts",
    __name__,
    url_prefix="/api/accounts"
)


# =====================================================
# CREATE A CUSTOMER ACCOUNT
# =====================================================

@accounts_bp.route("", methods=["POST"])
@roles_required("account_holder", "administrator")
def create_account():
    data = request.get_json(silent=True) or {}

    account_name = data.get("account_name")

    if not isinstance(account_name, str) or not account_name.strip():
        return jsonify({"error": "Account name is required"}), 400

    if len(account_name.strip()) > 120:
        return jsonify({"error": "Account name is too long"}), 400

    user = g.current_user

    if user.role == "account_holder":
        owner_user_id = user.id

    else:
        owner_user_id = data.get("owner_user_id")

        if (
            not isinstance(owner_user_id, int)
            or isinstance(owner_user_id, bool)
        ):
            return jsonify({
                "error": "Administrator must provide a valid owner_user_id"
            }), 400

        owner = db.session.get(User, owner_user_id)

        if (
            owner is None
            or not owner.is_active
            or owner.role != "account_holder"
        ):
            return jsonify({"error": "Invalid account owner"}), 400

    account = Account(
        account_number="LL" + uuid.uuid4().hex[:14].upper(),
        account_name=account_name.strip(),
        account_type="CUSTOMER",
        owner_user_id=owner_user_id,
        balance_paise=0,
        overdraft_enabled=False,
        overdraft_limit_paise=0,
        is_active=True,
    )

    try:
        db.session.add(account)
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Account creation failed"}), 409

    return jsonify({
        "message": "Account created successfully",
        "account": {
            "id": account.id,
            "account_number": account.account_number,
            "account_name": account.account_name,
            "balance_paise": account.balance_paise,
            "owner_user_id": account.owner_user_id,
        }
    }), 201


# =====================================================
# LIST ACCOUNTS
# =====================================================

@accounts_bp.route("", methods=["GET"])
@current_user_required
def list_accounts():
    user = g.current_user

    query = db.select(Account).where(
        Account.is_active.is_(True),
        Account.account_type == "CUSTOMER"
    )

    if user.role == "account_holder":
        query = query.where(Account.owner_user_id == user.id)

    accounts = db.session.execute(
        query.order_by(Account.id)
    ).scalars().all()

    return jsonify({
        "accounts": [
            {
                "id": account.id,
                "account_number": account.account_number,
                "account_name": account.account_name,
                "balance_paise": account.balance_paise,
            }
            for account in accounts
        ]
    }), 200


# =====================================================
# CHECK ACCOUNT BALANCE
# =====================================================

@accounts_bp.route("/<int:account_id>/balance", methods=["GET"])
@current_user_required
def get_balance(account_id):
    user = g.current_user

    account = db.session.get(Account, account_id)

    if account is None or not account.is_active:
        return jsonify({"error": "Account not found"}), 404

    if (
        user.role == "account_holder"
        and account.owner_user_id != user.id
    ):
        return jsonify({"error": "Access denied"}), 403

    return jsonify({
        "account_id": account.id,
        "account_number": account.account_number,
        "balance_paise": account.balance_paise,
        "balance_rupees": account.balance_paise / 100,
    }), 200


# =====================================================
# ACCOUNT STATEMENT
# =====================================================

@accounts_bp.route("/<int:account_id>/statement", methods=["GET"])
@current_user_required
def get_statement(account_id):
    user = g.current_user

    account = db.session.get(Account, account_id)

    if (
        account is None
        or not account.is_active
        or account.account_type != "CUSTOMER"
    ):
        return jsonify({"error": "Account not found"}), 404

    # Account-level authorization
    if (
        user.role == "account_holder"
        and account.owner_user_id != user.id
    ):
        return jsonify({"error": "Access denied"}), 403

    # Fetch successful ledger entries and their transactions.
    ledger_query = (
        select(LedgerEntry, LedgerTransaction, User)
        .join(
            LedgerTransaction,
            LedgerEntry.transaction_id == LedgerTransaction.id
        )
        .join(
            User,
            LedgerTransaction.initiated_by == User.id
        )
        .where(LedgerEntry.account_id == account_id)
        .order_by(
            LedgerEntry.created_at,
            LedgerEntry.id
        )
    )

    ledger_records = db.session.execute(ledger_query).all()

    statement = []

    for entry, transaction, initiator in ledger_records:
        statement.append({
            "record_type": "TRANSACTION",
            "transaction_id": transaction.id,
            "reference": str(transaction.transaction_reference),
            "transaction_type": transaction.transaction_type,
            "entry_side": entry.entry_side,
            "amount_paise": entry.amount_paise,
            "amount_rupees": entry.amount_paise / 100,
            "resulting_balance_paise": entry.resulting_balance_paise,
            "description": transaction.description,
            "initiated_by": initiator.username,
            "status": transaction.status,
            "created_at": entry.created_at.isoformat(),
            "_sort_time": entry.created_at,
            "_sort_id": entry.id,
        })

    # Fetch refused attempts for this account.
    attempts_query = (
        select(OperationAttempt, User)
        .outerjoin(
            User,
            OperationAttempt.user_id == User.id
        )
        .where(OperationAttempt.account_id == account_id)
        .order_by(
            OperationAttempt.created_at,
            OperationAttempt.id
        )
    )

    attempts = db.session.execute(attempts_query).all()

    for attempt, initiator in attempts:

        # Find the last recorded balance at or before the
        # refused attempt. Refused attempts do not change balances.
        previous_entry = db.session.execute(
            select(LedgerEntry)
            .where(
                LedgerEntry.account_id == account_id,
                LedgerEntry.created_at <= attempt.created_at,
            )
            .order_by(
                desc(LedgerEntry.created_at),
                desc(LedgerEntry.id),
            )
            .limit(1)
        ).scalar_one_or_none()

        balance_at_attempt = (
            previous_entry.resulting_balance_paise
            if previous_entry is not None
            else 0
        )

        statement.append({
            "record_type": "REFUSED_ATTEMPT",
            "transaction_id": None,
            "transaction_type": attempt.operation_type,
            "entry_side": None,
            "amount_paise": attempt.amount_paise,
            "amount_rupees": (
                attempt.amount_paise / 100
                if attempt.amount_paise is not None
                else None
            ),
            "resulting_balance_paise": balance_at_attempt,
            "description": attempt.reason,
            "initiated_by": (
                initiator.username if initiator else None
            ),
            "status": attempt.outcome,
            "created_at": attempt.created_at.isoformat(),
            "_sort_time": attempt.created_at,
            "_sort_id": attempt.id,
        })

    # Combine successful transactions and refused attempts chronologically.
    statement.sort(
        key=lambda item: (
            item["_sort_time"],
            item["record_type"],
            item["_sort_id"],
        )
    )

    # Remove internal sorting fields from the API response.
    for item in statement:
        item.pop("_sort_time")
        item.pop("_sort_id")

    return jsonify({
        "account_id": account.id,
        "account_number": account.account_number,
        "account_name": account.account_name,
        "current_balance_paise": account.balance_paise,
        "current_balance_rupees": account.balance_paise / 100,
        "statement_count": len(statement),
        "statement": statement,
    }), 200
