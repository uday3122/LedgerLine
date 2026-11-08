
import uuid

import pytest

from app import create_app, db
from app.models import User


@pytest.fixture
def app():
    application = create_app()
    yield application

    with application.app_context():
        db.session.remove()


@pytest.fixture
def client(app):
    return app.test_client()


def create_account_holder(client):
    unique = uuid.uuid4().hex[:10]

    username = f"holder_{unique}"
    email = f"{username}@example.com"
    password = "LedgerLine!2026"

    response = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password,
        },
    )
    assert response.status_code == 201, response.get_json()

    response = client.post(
        "/api/auth/login",
        json={
            "username": username,
            "password": password,
        },
    )
    assert response.status_code == 200, response.get_json()

    token = response.get_json()["access_token"]

    return {
        "username": username,
        "headers": {"Authorization": f"Bearer {token}"},
    }


def create_customer_account(client, headers, name):
    response = client.post(
        "/api/accounts",
        headers=headers,
        json={"account_name": name},
    )

    assert response.status_code == 201, response.get_json()

    return response.get_json()["account"]["id"]


def create_auditor(app):
    unique = uuid.uuid4().hex[:10]
    username = f"auditor_{unique}"

    auditor = User(
        username=username,
        email=f"{username}@example.com",
        role="auditor",
        is_active=True,
    )
    auditor.set_password("AuditorPassword!2026")

    with app.app_context():
        db.session.add(auditor)
        db.session.commit()

    return username


def login_auditor(client, username):
    response = client.post(
        "/api/auth/login",
        json={
            "username": username,
            "password": "AuditorPassword!2026",
        },
    )

    assert response.status_code == 200, response.get_json()

    token = response.get_json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


def test_authorization_matrix(app, client):

    # 1. Create two independent account holders.
    user_a = create_account_holder(client)
    user_b = create_account_holder(client)

    headers_a = user_a["headers"]
    headers_b = user_b["headers"]

    # 2. Each user creates their own account.
    account_a = create_customer_account(
        client, headers_a, "User A Account"
    )

    account_b = create_customer_account(
        client, headers_b, "User B Account"
    )

    # 3. User A must not see User B's account in the account list.
    response = client.get(
        "/api/accounts",
        headers=headers_a,
    )

    assert response.status_code == 200

    visible_ids = [
        account["id"]
        for account in response.get_json()["accounts"]
    ]

    assert account_a in visible_ids
    assert account_b not in visible_ids

    # 4. User A cannot view User B's balance.
    response = client.get(
        f"/api/accounts/{account_b}/balance",
        headers=headers_a,
    )
    assert response.status_code == 403

    # 5. User A cannot view User B's statement.
    response = client.get(
        f"/api/accounts/{account_b}/statement",
        headers=headers_a,
    )
    assert response.status_code == 403

    # 6. User A cannot withdraw from User B's account.
    response = client.post(
        "/api/transactions/withdraw",
        headers={
            **headers_a,
            "Idempotency-Key": str(uuid.uuid4()),
        },
        json={
            "account_id": account_b,
            "amount_paise": 100,
        },
    )
    assert response.status_code == 403

    # 7. User A cannot deposit into User B's account.
    response = client.post(
        "/api/transactions/deposit",
        headers={
            **headers_a,
            "Idempotency-Key": str(uuid.uuid4()),
        },
        json={
            "account_id": account_b,
            "amount_paise": 100,
        },
    )
    assert response.status_code == 403

    # 8. User A cannot transfer money from User B's account.
    response = client.post(
        "/api/transactions/transfer",
        headers={
            **headers_a,
            "Idempotency-Key": str(uuid.uuid4()),
        },
        json={
            "source_account_id": account_b,
            "destination_account_id": account_a,
            "amount_paise": 100,
        },
    )
    assert response.status_code == 403

    # 9. Provision an auditor and log in.
    auditor_username = create_auditor(app)
    auditor_headers = login_auditor(client, auditor_username)

    # 10. Auditor can view all customer accounts.
    response = client.get(
        "/api/accounts",
        headers=auditor_headers,
    )
    assert response.status_code == 200

    auditor_account_ids = [
        account["id"]
        for account in response.get_json()["accounts"]
    ]

    assert account_a in auditor_account_ids
    assert account_b in auditor_account_ids

    # 11. Auditor can view balances and statements.
    response = client.get(
        f"/api/accounts/{account_a}/balance",
        headers=auditor_headers,
    )
    assert response.status_code == 200

    response = client.get(
        f"/api/accounts/{account_a}/statement",
        headers=auditor_headers,
    )
    assert response.status_code == 200

    # 12. Auditor cannot create an account.
    response = client.post(
        "/api/accounts",
        headers=auditor_headers,
        json={"account_name": "Unauthorized Account"},
    )
    assert response.status_code == 403

    # 13. Auditor cannot deposit.
    response = client.post(
        "/api/transactions/deposit",
        headers={
            **auditor_headers,
            "Idempotency-Key": str(uuid.uuid4()),
        },
        json={
            "account_id": account_a,
            "amount_paise": 100,
        },
    )
    assert response.status_code == 403

    # 14. Auditor cannot withdraw.
    response = client.post(
        "/api/transactions/withdraw",
        headers={
            **auditor_headers,
            "Idempotency-Key": str(uuid.uuid4()),
        },
        json={
            "account_id": account_a,
            "amount_paise": 100,
        },
    )
    assert response.status_code == 403

    # 15. Auditor cannot transfer.
    response = client.post(
        "/api/transactions/transfer",
        headers={
            **auditor_headers,
            "Idempotency-Key": str(uuid.uuid4()),
        },
        json={
            "source_account_id": account_a,
            "destination_account_id": account_b,
            "amount_paise": 100,
        },
    )
    assert response.status_code == 403

    print("ALL AUTHORIZATION CHECKS PASSED")
