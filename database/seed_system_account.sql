INSERT INTO accounts (
    account_number,
    account_name,
    account_type,
    owner_user_id,
    balance_paise,
    overdraft_enabled,
    overdraft_limit_paise,
    is_active
)
VALUES (
    'SYSTEM-CLEARING-001',
    'System Clearing Account',
    'SYSTEM',
    NULL,
    0,
    FALSE,
    0,
    TRUE
)
ON CONFLICT (account_number) DO NOTHING;