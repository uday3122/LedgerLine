from sqlalchemy import text
from app import create_app, db

app = create_app()

with app.app_context():
    query = text("""
        SELECT
            a.id,
            a.account_name,
            a.balance_paise AS stored_balance,
            COALESCE(
                SUM(
                    CASE
                        WHEN e.entry_side = 'CREDIT' THEN e.amount_paise
                        WHEN e.entry_side = 'DEBIT' THEN -e.amount_paise
                        ELSE 0
                    END
                ), 0
            ) AS ledger_balance
        FROM accounts a
        LEFT JOIN ledger_entries e ON e.account_id = a.id
        GROUP BY a.id, a.account_name, a.balance_paise
        ORDER BY a.id
    """)

    rows = db.session.execute(query).mappings().all()

    print("TOTAL ACCOUNTS CHECKED:", len(rows))

    problems = [
        dict(row) for row in rows
        if row["stored_balance"] != row["ledger_balance"]
    ]

    print("BALANCE MISMATCHES:", len(problems))

    for problem in problems:
        print(problem)

    if not problems:
        print("RESULT: ALL ACCOUNT BALANCES MATCH LEDGER")
    else:
        print("RESULT: BALANCE MISMATCH FOUND")
