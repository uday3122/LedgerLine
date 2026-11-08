-- LedgerLine database schema
-- Monetary values are stored in paise (BIGINT), never FLOAT.

CREATE TABLE IF NOT EXISTS users (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role VARCHAR(20) NOT NULL
        CHECK (role IN ('administrator', 'account_holder', 'auditor')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS accounts (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_number VARCHAR(30) NOT NULL UNIQUE,
    account_name VARCHAR(120) NOT NULL,
    account_type VARCHAR(20) NOT NULL DEFAULT 'CUSTOMER'
        CHECK (account_type IN ('CUSTOMER', 'SYSTEM')),
    owner_user_id BIGINT REFERENCES users(id),
    balance_paise BIGINT NOT NULL DEFAULT 0,
    overdraft_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    overdraft_limit_paise BIGINT NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (overdraft_limit_paise >= 0),
    CHECK (
        overdraft_enabled = TRUE
        OR overdraft_limit_paise = 0
    ),
    CHECK (
        account_type = 'SYSTEM'
        OR (
            overdraft_enabled = TRUE
            AND balance_paise >= -overdraft_limit_paise
        )
        OR (
            overdraft_enabled = FALSE
            AND balance_paise >= 0
        )
    ),
    CHECK (
        (account_type = 'SYSTEM' AND owner_user_id IS NULL)
        OR
        (account_type = 'CUSTOMER' AND owner_user_id IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS ledger_transactions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transaction_reference UUID NOT NULL UNIQUE,
    transaction_type VARCHAR(20) NOT NULL
        CHECK (transaction_type IN ('DEPOSIT', 'WITHDRAWAL', 'TRANSFER')),
    status VARCHAR(20) NOT NULL DEFAULT 'POSTED'
        CHECK (status IN ('POSTED')),
    amount_paise BIGINT NOT NULL CHECK (amount_paise > 0),
    description TEXT,
    initiated_by BIGINT REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ledger_entries (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transaction_id BIGINT NOT NULL
        REFERENCES ledger_transactions(id),
    account_id BIGINT NOT NULL REFERENCES accounts(id),
    entry_side VARCHAR(10) NOT NULL
        CHECK (entry_side IN ('DEBIT', 'CREDIT')),
    amount_paise BIGINT NOT NULL CHECK (amount_paise > 0),
    resulting_balance_paise BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ledger_entries_account
    ON ledger_entries(account_id, id);

CREATE INDEX IF NOT EXISTS idx_ledger_entries_transaction
    ON ledger_entries(transaction_id);

CREATE TABLE IF NOT EXISTS idempotency_keys (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    idempotency_key VARCHAR(150) NOT NULL,
    request_hash VARCHAR(64) NOT NULL,
    transaction_id BIGINT REFERENCES ledger_transactions(id),
    response_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (user_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS operation_attempts (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    account_id BIGINT REFERENCES accounts(id),
    operation_type VARCHAR(30) NOT NULL,
    amount_paise BIGINT,
    outcome VARCHAR(20) NOT NULL
        CHECK (outcome IN ('REFUSED', 'FAILED')),
    reason TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_operation_attempts_account
    ON operation_attempts(account_id, id);

CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Prevent changes to posted ledger entries.
CREATE OR REPLACE FUNCTION prevent_ledger_entry_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'Ledger entries are append-only and cannot be updated or deleted';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS ledger_entries_no_update
    ON ledger_entries;

CREATE TRIGGER ledger_entries_no_update
BEFORE UPDATE OR DELETE ON ledger_entries
FOR EACH ROW
EXECUTE FUNCTION prevent_ledger_entry_mutation();

-- Prevent changes to posted transaction records.
CREATE OR REPLACE FUNCTION prevent_ledger_transaction_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'Posted transactions cannot be updated or deleted';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS ledger_transactions_no_update
    ON ledger_transactions;

CREATE TRIGGER ledger_transactions_no_update
BEFORE UPDATE OR DELETE ON ledger_transactions
FOR EACH ROW
EXECUTE FUNCTION prevent_ledger_transaction_mutation();