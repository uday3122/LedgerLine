
# LedgerLine API Documentation

Base URL: `http://127.0.0.1:5000`

## Authentication

### Register
`POST /register`

Request:
```json
{
  "username": "user1",
  "email": "user1@example.com",
  "password": "StrongPassword!2026"
}
```

### Login
`POST /login`

Returns a JWT access token.

### Current User
`GET /me`

Requires JWT authentication.

## Accounts

All endpoints require authentication.

- `POST /api/accounts` — Create an account.
- `GET /api/accounts` — List permitted accounts.
- `GET /api/accounts/<account_id>/balance` — View balance.
- `GET /api/accounts/<account_id>/statement` — View statement.

## Transactions

All transaction endpoints require authentication and an `Idempotency-Key` header.

- `POST /api/transactions/deposit`
- `POST /api/transactions/withdraw`
- `POST /api/transactions/transfer`

Amounts are represented in integer paise.

## Authorization

- Account holders can operate on their own source accounts.
- Administrators can manage permitted accounts.
- Auditors have read-only access.

## Important

Use the actual request fields and response formats implemented in the application. This document provides the endpoint overview.
