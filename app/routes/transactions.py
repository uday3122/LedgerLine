
from flask import Blueprint, request, jsonify, g

from app import db
from app.models import Account, OperationAttempt
from app.utils.auth_helpers import roles_required

from app.services.transaction_service import (
    move_money,
    deposit_money,
    withdraw_money,
    TransactionError,
)


transactions_bp = Blueprint(
    "transactions",
    __name__,
    url_prefix="/api/transactions"
)


# =====================================================
# TRANSFER MONEY
# =====================================================

@transactions_bp.route("/transfer", methods=["POST"])
@roles_required("account_holder", "administrator")
def transfer():
    data = request.get_json(silent=True) or {}

    source_id = data.get("source_account_id")
    destination_id = data.get("destination_account_id")
    amount = data.get("amount_paise")

    if (
        not isinstance(source_id, int)
        or isinstance(source_id, bool)
        or not isinstance(destination_id, int)
        or isinstance(destination_id, bool)
        or not isinstance(amount, int)
        or isinstance(amount, bool)
    ):
        return jsonify({
            "error": "Account IDs and amount_paise must be integers"
        }), 400

    user = g.current_user

    source = db.session.get(Account, source_id)

    if source is None or not source.is_active:
        return jsonify({"error": "Source account not found"}), 404

    if (
        user.role == "account_holder"
        and source.owner_user_id != user.id
    ):
        return jsonify({"error": "Access denied"}), 403

    try:
        result = move_money(
            transaction_type="TRANSFER",
            source_account_id=source_id,
            destination_account_id=destination_id,
            amount_paise=amount,
            initiated_by=user.id,
            idempotency_key=request.headers.get("Idempotency-Key"),
            description=data.get("description"),
        )

        return jsonify(result), 201

    except TransactionError as error:
        db.session.rollback()

        attempt = OperationAttempt(
            user_id=user.id,
            account_id=source_id,
            operation_type="TRANSFER",
            amount_paise=amount if amount > 0 else None,
            outcome="REFUSED",
            reason=str(error),
        )

        db.session.add(attempt)
        db.session.commit()

        return jsonify({"error": str(error)}), 400

    except Exception:
        db.session.rollback()
        return jsonify({"error": "Transfer failed"}), 500


# =====================================================
# DEPOSIT MONEY
# =====================================================

@transactions_bp.route("/deposit", methods=["POST"])
@roles_required("account_holder", "administrator")
def deposit():
    data = request.get_json(silent=True) or {}

    account_id = data.get("account_id")
    amount = data.get("amount_paise")

    if (
        not isinstance(account_id, int)
        or isinstance(account_id, bool)
        or not isinstance(amount, int)
        or isinstance(amount, bool)
    ):
        return jsonify({
            "error": "account_id and amount_paise must be integers"
        }), 400

    user = g.current_user

    account = db.session.get(Account, account_id)

    if account is None or not account.is_active:
        return jsonify({"error": "Account not found"}), 404

    if (
        user.role == "account_holder"
        and account.owner_user_id != user.id
    ):
        return jsonify({"error": "Access denied"}), 403

    try:
        result = deposit_money(
            account_id=account_id,
            amount_paise=amount,
            initiated_by=user.id,
            idempotency_key=request.headers.get("Idempotency-Key"),
            description=data.get("description"),
        )

        return jsonify(result), 201

    except TransactionError as error:
        db.session.rollback()

        attempt = OperationAttempt(
            user_id=user.id,
            account_id=account_id,
            operation_type="DEPOSIT",
            amount_paise=amount if amount > 0 else None,
            outcome="REFUSED",
            reason=str(error),
        )

        db.session.add(attempt)
        db.session.commit()

        return jsonify({"error": str(error)}), 400

    except Exception:
        db.session.rollback()
        return jsonify({"error": "Deposit failed"}), 500


# =====================================================
# WITHDRAW MONEY
# =====================================================

@transactions_bp.route("/withdraw", methods=["POST"])
@roles_required("account_holder", "administrator")
def withdraw():
    data = request.get_json(silent=True) or {}

    account_id = data.get("account_id")
    amount = data.get("amount_paise")

    if (
        not isinstance(account_id, int)
        or isinstance(account_id, bool)
        or not isinstance(amount, int)
        or isinstance(amount, bool)
    ):
        return jsonify({
            "error": "account_id and amount_paise must be integers"
        }), 400

    user = g.current_user

    account = db.session.get(Account, account_id)

    if account is None or not account.is_active:
        return jsonify({"error": "Account not found"}), 404

    if (
        user.role == "account_holder"
        and account.owner_user_id != user.id
    ):
        return jsonify({"error": "Access denied"}), 403

    try:
        result = withdraw_money(
            account_id=account_id,
            amount_paise=amount,
            initiated_by=user.id,
            idempotency_key=request.headers.get("Idempotency-Key"),
            description=data.get("description"),
        )

        return jsonify(result), 201

    except TransactionError as error:
        db.session.rollback()

        attempt = OperationAttempt(
            user_id=user.id,
            account_id=account_id,
            operation_type="WITHDRAWAL",
            amount_paise=amount if amount > 0 else None,
            outcome="REFUSED",
            reason=str(error),
        )

        db.session.add(attempt)
        db.session.commit()

        return jsonify({"error": str(error)}), 400

    except Exception:
        db.session.rollback()
        return jsonify({"error": "Withdrawal failed"}), 500
