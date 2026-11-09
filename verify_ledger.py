from sqlalchemy import text
from app import create_app, db

app = create_app()

with app.app_context():
    query = text("""
        SELECT
            t.id,
            t.transaction_type,
            t.amount_paise,
            COUNT(e.id) AS entry_count,
            COALESCE(SUM(CASE WHEN e.entry_side = 'DEBIT'
                THEN e.amount_paise ELSE 0 END), 0) AS debit_total,
            COALESCE(SUM(CASE WHEN e.entry_side = 'CREDIT'
                THEN e.amount_paise ELSE 0 END), 0) AS credit_total
        FROM ledger_transactions t
        LEFT JOIN ledger_entries e ON e.transaction_id = t.id
        WHERE t.status = 'POSTED'
        GROUP BY t.id, t.transaction_type, t.amount_paise
        ORDER BY t.id
    """)

    rows = db.session.execute(query).mappings().all()

    print("POSTED TRANSACTIONS:", len(rows))

    problems = [
        dict(row) for row in rows
        if row["entry_count"] != 2
        or row["debit_total"] != row["credit_total"]
        or row["debit_total"] != row["amount_paise"]
    ]

    print("UNBALANCED OR INVALID TRANSACTIONS:", len(problems))

    for problem in problems:
        print(problem)

    if not problems:
        print("RESULT: ALL POSTED TRANSACTIONS BALANCED")
    else:
        print("RESULT: CHECK REQUIRED")
