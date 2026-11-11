# LedgerLine API Documentation

## Base URL

Local:

```text
http://127.0.0.1:5000
```

Deployed:

```text
https://YOUR-RENDER-SERVICE.onrender.com
```

Replace the deployed example with the actual Render public URL.

## Authentication

Protected endpoints require a JWT access token.

Include the following HTTP header:

```http
Authorization: Bearer YOUR_ACCESS_TOKEN
```

### 1. Register User

**POST** `/api/auth/register`

Request:

```json
{
  "username": "user1",
  "email": "user1@example.com",
  "password": "StrongPassword!2026"
}
```

Success response: `201 Created`

Example:

```json
{
  "message": "Registration successful",
  "user": {
    "id": 1,
    "username": "user1",
    "email": "user1@example.com",
    "role": "account_holder"
  }
}
```

Validation includes required fields, maximum username/email lengths and a minimum password length of 12 characters.

### 2. Login

**POST** `/api/auth/login`

Request:

```json
{
  "username": "user1",
  "password": "StrongPassword!2026"
}
```

Success response: `200 OK`

Returns an `access_token` and user details. Use the returned token as a Bearer token for protected API calls.

### 3. Current User

**GET** `/api/auth/me`

Authentication required.

Returns the authenticated user's ID, username, email and role.

## Account APIs

All account APIs require authentication.

### 4. Create Account

**POST** `/api/accounts`

Account Holder request:

```json
{
  "account_name": "Primary Savings Account"
}
```

Administrator requests must additionally provide a valid `owner_user_id`.

Success response: `201 Created`.

### 5. List Accounts

**GET** `/api/accounts`

Returns the customer accounts permitted for the authenticated role.

### 6. Check Balance

**GET** `/api/accounts/<account_id>/balance`

Returns:

- Account ID
- Account number
- Balance in paise
- Balance in rupees

Example:

```json
{
  "account_id": 1,
  "account_number": "LL123456789ABCDE",
  "balance_paise": 10000,
  "balance_rupees": 100.0
}
```

### 7. Account Statement

**GET** `/api/accounts/<account_id>/statement`

Returns the current balance and chronological account statement.

The response can include:

- Posted transactions.
- Debit or credit entry side.
- Transaction reference and transaction ID.
- Amount and resulting balance.
- Refused operation attempts.

## Transaction APIs

All transaction endpoints require authentication and an `Idempotency-Key` header.

Amounts must be positive integer paise.

For example:

```text
₹100 = 10000 paise
₹30  = 3000 paise
₹20  = 2000 paise
```

### 8. Deposit

**POST** `/api/transactions/deposit`

Headers:

```http
Authorization: Bearer YOUR_ACCESS_TOKEN
Idempotency-Key: unique-deposit-request-001
```

Request:

```json
{
  "account_id": 1,
  "amount_paise": 10000,
  "description": "Initial deposit"
}
```

Success response: `201 Created`.

### 9. Withdraw

**POST** `/api/transactions/withdraw`

Headers:

```http
Authorization: Bearer YOUR_ACCESS_TOKEN
Idempotency-Key: unique-withdraw-request-001
```

Request:

```json
{
  "account_id": 1,
  "amount_paise": 2000,
  "description": "Cash withdrawal"
}
```

Success response: `201 Created`.

Insufficient-funds and other transaction validation failures return an error response.

### 10. Transfer

**POST** `/api/transactions/transfer`

Headers:

```http
Authorization: Bearer YOUR_ACCESS_TOKEN
Idempotency-Key: unique-transfer-request-001
```

Request:

```json
{
  "source_account_id": 1,
  "destination_account_id": 2,
  "amount_paise": 3000,
  "description": "Internal account transfer"
}
```

Success response: `201 Created`.

A successful transfer creates a debit entry for the source account and a credit entry for the destination account.

## Idempotency Behaviour

A unique `Idempotency-Key` must be supplied for each transaction request.

- Same key and same request: the original result is returned.
- Same key and different request: the request is rejected.
- A completed request is not posted a second time.

Use a new idempotency key for each new intended transaction. Reuse the original key only when retrying that same request.

## Authorization

| Role | Permissions |
|---|---|
| Account Holder | Create and operate own accounts; view permitted account data |
| Administrator | Manage permitted accounts and perform permitted transactions |
| Auditor | Read-only account and statement access |

Account ownership is checked by the server for account-holder access.

## Common HTTP Status Codes

| Status | Meaning |
|---|---|
| 200 | Request succeeded |
| 201 | Resource or transaction created |
| 400 | Validation or transaction error |
| 401 | Authentication required or invalid |
| 403 | Access denied |
| 404 | Account or resource not found |
| 409 | Duplicate username/email or conflicting creation |

Actual error responses depend on the endpoint and validation failure.

## Important Notes

1. Never send passwords or JWT tokens in public messages.
2. Keep the database URL and signing secrets private.
3. Use integer paise for transaction amounts.
4. Do not reuse idempotency keys for different operations.
5. This API is a hackathon demonstration and is not a real-money payment gateway.
