
from sqlalchemy import inspect

from app import create_app, db
from app.models import (
    User,
    Account,
    LedgerTransaction,
    LedgerEntry,
    IdempotencyKey,
    OperationAttempt,
    AuditLog,
)

app = create_app()

with app.app_context():
    try:
        inspector = inspect(db.engine)

        database_tables = set(
            inspector.get_table_names(schema="public")
        )

        expected_tables = {
            "users",
            "accounts",
            "ledger_transactions",
            "ledger_entries",
            "idempotency_keys",
            "operation_attempts",
            "audit_logs",
        }

        missing_tables = expected_tables - database_tables

        if missing_tables:
            raise RuntimeError(
                f"Missing database tables: {missing_tables}"
            )

        print("DATABASE CONNECTION SUCCESSFUL!")
        print("ALL 7 DATABASE TABLES VERIFIED!")
        print("ALL 7 PYTHON MODELS LOADED SUCCESSFULLY!")

        for table in sorted(expected_tables):
            print("  -", table)

    except Exception as error:
        print("MODEL VERIFICATION FAILED!")
        print("Error:", error)
        raise
    if __name__ == "__main__":
        app.run(
            host="127.0.0.1",
            port=5000,
            debug=True
        )
