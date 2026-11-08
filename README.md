
# LedgerLine — Money Movement with a Ledger You Can Prove

LedgerLine is a secure money movement application built using Python, Flask and PostgreSQL.

It supports account management, deposits, withdrawals, transfers, transaction history and idempotent money operations.

## Technology Stack

- Python
- Flask
- PostgreSQL
- Flask-JWT-Extended
- SQLAlchemy
- Pytest

## Features

- User registration and login using JWT authentication.
- Three roles: Administrator, Account Holder and Auditor.
- Create accounts and view account balances.
- Deposit, withdraw and transfer money.
- Idempotency keys to prevent duplicate transactions.
- PostgreSQL transactions and row-level locking.
- Double-entry ledger records.
- Append-only ledger protection using database triggers.
- Account statements with transaction history.
- Automated authorization tests.

## Project Structure

```text
LedgerLine/
├── app/
│   ├── models/
│   ├── routes/
│   ├── services/
│   └── utils/
├── database/
│   └── schema.sql
├── docs/
├── tests/
├── config.py
├── run.py
├── requirements.txt
├── API.md
├── THREATS.md
├── PROMPTS.md
└── README.md
```

## Setup

1. Clone or download the repository.
2. Create and activate a virtual environment.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create a PostgreSQL database named `ledgerline_db`.
5. Execute the database schema:

```bash
psql -U postgres -h localhost -p 5432 -d ledgerline_db -f database/schema.sql
```

6. Create a `.env` file using `.env.example` as a template.
7. Add your own database URL and secret keys.

## Run the Application

```bash
python run.py
```

## Run Automated Tests

```bash
pytest -v
```

Run the manual API and concurrency checks separately:

```bash
python tests/manual_api_check.py
```

## Security Notes

- Never commit `.env` or expose passwords and secret keys.
- Account ownership is checked on the server.
- Financial operations use database transactions.
- Ledger records are protected against updates and deletions.

## Testing Status

The authorization test passed. Manual API checks also passed for deposit replay, transfers, withdrawals, refused withdrawals and a simultaneous withdrawal scenario.

These results represent the tests currently performed, not a guarantee of complete production security.
