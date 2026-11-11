# LedgerLine — Money Movement with a Ledger You Can Prove

## Project Overview

LedgerLine is a money movement application built using Python, Flask and PostgreSQL. It provides account management, deposits, withdrawals, transfers and transaction statements backed by a double-entry ledger.

The system focuses on transaction integrity, duplicate-request prevention, account ownership, concurrency safety and verifiable financial records.

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, Flask |
| Database | PostgreSQL |
| ORM | Flask-SQLAlchemy, SQLAlchemy |
| Authentication | Flask-JWT-Extended |
| Database driver | Psycopg |
| Testing | Pytest, manual API tests |
| Deployment | Render |
| Version control | Git, GitHub |

## Main Features

1. User registration and JWT-based authentication.
2. Administrator, Account Holder and Auditor roles.
3. Customer account creation and balance enquiries.
4. Deposits, withdrawals and account-to-account transfers.
5. Idempotency keys to prevent duplicate financial operations.
6. PostgreSQL transactions and row-level locking.
7. Double-entry debit and credit ledger entries.
8. Database-trigger protection for posted ledger records.
9. Transaction statements and refused-operation records.
10. Server-side account ownership and role authorization.

## Transaction Integrity

LedgerLine uses integer paise rather than floating-point values for financial amounts.

Each posted financial transaction produces corresponding debit and credit ledger entries. The entries are committed together with account balance changes.

Idempotency keys protect against repeated requests. Reusing the same key with the same request returns the original result instead of executing the operation again.

Database row locking helps prevent concurrent transactions from spending the same available balance.

## Project Architecture

The application follows a Flask application-factory structure:

- `app/models/` — database models.
- `app/routes/` — authentication, account and transaction APIs.
- `app/services/` — financial transaction processing.
- `app/utils/` — authentication and authorization helpers.
- `database/` — PostgreSQL schema and system-account initialization.
- `tests/` — authorization and manual API tests.

## Repository Structure

```text
LedgerLine/
├── app/
│   ├── models/
│   ├── routes/
│   ├── services/
│   ├── utils/
│   └── __init__.py
├── database/
│   ├── schema.sql
│   └── seed_system_account.sql
├── docs/
├── tests/
│   ├── test_authorization.py
│   └── manual_api_check.py
├── config.py
├── run.py
├── requirements.txt
├── .env.example
├── API.md
├── THREATS.md
├── PROMPTS.md
├── verify_balances.py
├── verify_ledger.py
└── README.md
```

## Local Installation

### 1. Clone the repository

```bash
git clone https://github.com/uday3122/LedgerLine.git
cd LedgerLine
```

### 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure PostgreSQL

Create a PostgreSQL database named:

```text
ledgerline_db
```

Apply the database schema:

```bash
psql -U postgres -h localhost -p 5432 -d ledgerline_db -f database/schema.sql
```

Initialize the system clearing account:

```bash
psql -U postgres -h localhost -p 5432 -d ledgerline_db -f database/seed_system_account.sql
```

### 5. Configure environment variables

Create `.env` from `.env.example` and configure:

```env
SECRET_KEY=your-secret-value
JWT_SECRET_KEY=your-jwt-secret-value
DATABASE_URL=postgresql+psycopg://username:password@localhost:5432/ledgerline_db
```

Use different strong secret values. Never commit `.env` or expose database credentials.

### 6. Start the application

```bash
python run.py
```

Local base URL:

```text
http://127.0.0.1:5000
```

## Deployment on Render

LedgerLine has been deployed as a Python Flask Web Service with a hosted PostgreSQL database.

The configured service uses:

**Build command**

```bash
pip install -r requirements.txt && pip install gunicorn
```

**Start command**

```bash
gunicorn --bind 0.0.0.0:$PORT 'app:create_app()'
```

Configure these environment variables in Render:

- `SECRET_KEY`
- `JWT_SECRET_KEY`
- `DATABASE_URL`

Use the PostgreSQL Internal Database URL for the web service. The application database URL must use the compatible `postgresql+psycopg://` driver prefix.

Live application URL:

```text
https://ledgerline-api-cg5p.onrender.com
```

## API Documentation

See [API.md](API.md) for authentication, account, transaction endpoints, request examples and authorization requirements.

All transaction amounts are supplied in integer paise.

## Testing

Run the automated tests:

```bash
pytest -v
```

Run manual API and concurrency checks:

```bash
python tests/manual_api_check.py
```

Additional ledger verification scripts:

```bash
python verify_ledger.py
python verify_balances.py
```

Run the verification scripts only after configuring the intended database connection.

## Verified Project Results

The following checks have been performed during development:

- Authorization test passed locally.
- Manual API and concurrency checks passed locally.
- Posted ledger transactions were checked for matching debit and credit totals.
- Account balances were compared against ledger-derived balances.
- Live Render registration and login succeeded.
- Live account creation succeeded.
- Live deposit succeeded.
- Replaying an identical deposit request returned the original transaction.
- Live transfer and withdrawal operations succeeded.
- Live transaction statements were reconciled with the returned balances.

The live test database contains demonstration transactions. These are test records, not real-money movements.

## Security and Limitations

- JWT authentication protects authenticated endpoints.
- Account ownership is checked on the server.
- Financial operations use PostgreSQL database transactions.
- Idempotency keys help prevent duplicate operations.
- Database triggers protect posted ledger entries from application-level modification.
- Secrets are supplied through environment variables.

LedgerLine is a hackathon demonstration project. Additional independent security review, production monitoring, operational controls and payment-provider integration would be required before real-money production use.

## Project Repository

GitHub: https://github.com/uday3122/LedgerLine
