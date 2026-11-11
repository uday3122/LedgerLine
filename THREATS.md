# LedgerLine — Threat Analysis

## Overview

This document records important application risks and the controls implemented in LedgerLine. It also identifies areas that require additional work before production use.

## 1. Unauthorized Account Access

**Threat:** A user attempts to read or operate another user's account.

**Implemented controls:**
- JWT authentication.
- Role-based route protection.
- Server-side account ownership checks.
- Read-only access restrictions for auditors.

## 2. Duplicate Transactions

**Threat:** Network retries or repeated client requests cause money to be moved more than once.

**Implemented controls:**
- Idempotency keys.
- Database uniqueness constraints.
- Request hashing.
- Previously completed results are returned for identical retries.

## 3. Concurrent Withdrawals

**Threat:** Two simultaneous withdrawals attempt to use the same available balance.

**Implemented controls:**
- PostgreSQL row-level locking.
- Consistent account-lock ordering.
- Database transactions.
- Balance validation while account rows are locked.

## 4. Ledger Tampering

**Threat:** Posted financial records are modified or deleted.

**Implemented controls:**
- Append-only protection through PostgreSQL triggers.
- Ledger entries are linked to posted transactions.
- Debit and credit entries are checked through verification scripts.

The database administration environment remains a trusted security boundary.

## 5. Insufficient Funds and Invalid Amounts

**Threat:** A user attempts to withdraw more than the available balance or submits an invalid amount.

**Implemented controls:**
- Positive integer amount validation.
- Server-side balance checks.
- Overdraft rules.
- Account locking during transaction processing.
- Refused attempts can be recorded in account statements.

## 6. Credential Exposure

**Threat:** Database credentials, application secrets or JWT signing keys are exposed.

**Implemented controls:**
- Environment-variable configuration.
- `.env` is excluded from Git.
- Separate application and JWT secret settings.

## 7. Unauthorized Transaction Ownership

**Threat:** A user tries to use an account that belongs to another user as the source of a transaction.

**Implemented controls:**
- Server-side ownership verification in transaction routes.
- Role restrictions for transaction operations.

## 8. Transaction Failure

**Threat:** An error occurs after a balance update but before ledger recording is completed.

**Implemented controls:**
- Database transaction boundaries.
- Commit only after the related balance, transaction and ledger records are prepared.
- Rollback when an exception occurs.

## Verification Performed

- Local authorization tests.
- Manual deposit, withdrawal and transfer checks.
- Duplicate deposit replay checks.
- Concurrent withdrawal tests.
- Ledger debit/credit verification.
- Account balance-to-ledger reconciliation.
- Live registration, login and transaction tests on Render.

## Remaining Production Considerations

The following should be evaluated before any real-money deployment:

- Independent penetration testing.
- Rate limiting and abuse monitoring.
- Multi-factor authentication.
- Centralized logging and alerting.
- Backup and recovery procedures.
- Stronger operational controls for administrators.
- Payment-provider integration and regulatory compliance.
- Production database availability and monitoring.

## Conclusion

LedgerLine implements application-level controls for authentication, account ownership, idempotency, transaction atomicity, concurrency and ledger integrity. The implemented tests provide evidence for the scenarios tested, but do not replace a full independent security audit.
