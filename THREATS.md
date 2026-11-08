
# Threat Analysis

## 1. Unauthorized Access
Risk: A user may try to access another user's account.

Mitigation: JWT authentication and server-side account ownership checks.

## 2. Duplicate Transactions
Risk: Repeated requests may move money more than once.

Mitigation: Idempotency keys and database uniqueness constraints.

## 3. Concurrent Withdrawals
Risk: Simultaneous withdrawals may cause an incorrect balance.

Mitigation: PostgreSQL row-level locking and database transactions.

## 4. Ledger Tampering
Risk: Posted financial records may be modified or deleted.

Mitigation: Database triggers prevent updates and deletions on ledger tables.

## 5. Negative Balance
Risk: Withdrawals may exceed available funds.

Mitigation: Server-side balance and overdraft checks.

## 6. Secret Exposure
Risk: Database credentials or JWT secrets may leak.

Mitigation: Store secrets in environment variables and exclude `.env` from Git.
