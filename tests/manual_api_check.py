
import os
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from app import create_app

app = create_app()


def check_response(response, expected_status, step):
    print(f"\n{step}")
    print("Status:", response.status_code)

    try:
        data = response.get_json()
    except Exception:
        data = None

    print("Response:", data)

    if response.status_code != expected_status:
        raise AssertionError(
            f"{step} failed. Expected {expected_status}, "
            f"received {response.status_code}"
        )

    return data


def main():
    with app.test_client() as client:

        unique_id = uuid.uuid4().hex[:8]

        # =========================================
        # 1. REGISTER USER
        # =========================================

        username = f"testuser_{unique_id}"
        email = f"test_{unique_id}@example.com"
        password = "LedgerLine@2026"

        register_response = client.post(
            "/api/auth/register",
            json={
                "username": username,
                "email": email,
                "password": password,
            },
        )

        check_response(
            register_response,
            201,
            "REGISTER USER",
        )

        # =========================================
        # 2. LOGIN USER
        # =========================================

        login_response = client.post(
            "/api/auth/login",
            json={
                "username": username,
                "password": password,
            },
        )

        login_data = check_response(
            login_response,
            200,
            "LOGIN USER",
        )

        token = login_data["access_token"]

        headers = {
            "Authorization": f"Bearer {token}",
        }

        # =========================================
        # 3. CREATE FIRST ACCOUNT
        # =========================================

        account1_response = client.post(
            "/api/accounts",
            json={
                "account_name": "Primary Test Account",
            },
            headers=headers,
        )

        account1_data = check_response(
            account1_response,
            201,
            "CREATE FIRST ACCOUNT",
        )

        account1_id = account1_data["account"]["id"]

        # =========================================
        # 4. CREATE SECOND ACCOUNT
        # =========================================

        account2_response = client.post(
            "/api/accounts",
            json={
                "account_name": "Secondary Test Account",
            },
            headers=headers,
        )

        account2_data = check_response(
            account2_response,
            201,
            "CREATE SECOND ACCOUNT",
        )

        account2_id = account2_data["account"]["id"]

        # =========================================
        # 5. DEPOSIT ₹100
        # =========================================

        deposit_key = f"deposit-{unique_id}"

        deposit_headers = {
            **headers,
            "Idempotency-Key": deposit_key,
        }

        deposit_payload = {
            "account_id": account1_id,
            "amount_paise": 10000,
            "description": "Initial test deposit",
        }

        deposit_response = client.post(
            "/api/transactions/deposit",
            json=deposit_payload,
            headers=deposit_headers,
        )

        deposit_data = check_response(
            deposit_response,
            201,
            "DEPOSIT ₹100",
        )

        # =========================================
        # 6. REPLAY SAME DEPOSIT
        # =========================================

        replay_response = client.post(
            "/api/transactions/deposit",
            json=deposit_payload,
            headers=deposit_headers,
        )

        replay_data = check_response(
            replay_response,
            201,
            "REPLAY DEPOSIT REQUEST",
        )

        assert (
            replay_data["transaction_id"]
            == deposit_data["transaction_id"]
        ), "Duplicate deposit created another transaction"

        print("PASS: Deposit replay did not create another transaction")

        # =========================================
        # 7. TRANSFER ₹30
        # =========================================

        transfer_response = client.post(
            "/api/transactions/transfer",
            json={
                "source_account_id": account1_id,
                "destination_account_id": account2_id,
                "amount_paise": 3000,
                "description": "Test internal transfer",
            },
            headers={
                **headers,
                "Idempotency-Key": f"transfer-{unique_id}",
            },
        )

        check_response(
            transfer_response,
            201,
            "TRANSFER ₹30",
        )

        # =========================================
        # 8. WITHDRAW ₹20
        # =========================================

        withdrawal_response = client.post(
            "/api/transactions/withdraw",
            json={
                "account_id": account1_id,
                "amount_paise": 2000,
                "description": "Test withdrawal",
            },
            headers={
                **headers,
                "Idempotency-Key": f"withdraw-{unique_id}",
            },
        )

        check_response(
            withdrawal_response,
            201,
            "WITHDRAW ₹20",
        )

        # =========================================
        # 9. REFUSED WITHDRAWAL
        # =========================================

        refused_response = client.post(
            "/api/transactions/withdraw",
            json={
                "account_id": account1_id,
                "amount_paise": 6000,
                "description": "Test insufficient funds",
            },
            headers={
                **headers,
                "Idempotency-Key": f"refused-{unique_id}",
            },
        )

        check_response(
            refused_response,
            400,
            "REFUSED WITHDRAWAL",
        )

        # =========================================
        # 10. CHECK FIRST ACCOUNT BALANCE
        # =========================================

        balance1_response = client.get(
            f"/api/accounts/{account1_id}/balance",
            headers=headers,
        )

        balance1_data = check_response(
            balance1_response,
            200,
            "FIRST ACCOUNT BALANCE",
        )

        assert balance1_data["balance_paise"] == 5000

        # =========================================
        # 11. CHECK SECOND ACCOUNT BALANCE
        # =========================================

        balance2_response = client.get(
            f"/api/accounts/{account2_id}/balance",
            headers=headers,
        )

        balance2_data = check_response(
            balance2_response,
            200,
            "SECOND ACCOUNT BALANCE",
        )

        assert balance2_data["balance_paise"] == 3000

        # =========================================
        # 12. CHECK FIRST ACCOUNT STATEMENT
        # =========================================

        statement_response = client.get(
            f"/api/accounts/{account1_id}/statement",
            headers=headers,
        )

        statement_data = check_response(
            statement_response,
            200,
            "FIRST ACCOUNT STATEMENT",
        )

        assert statement_data["current_balance_paise"] == 5000

        assert any(
            item["record_type"] == "REFUSED_ATTEMPT"
            for item in statement_data["statement"]
        ), "Refused attempt missing from statement"

        print("PASS: Refused attempt appears in statement")

        # =========================================
        # 13. CONCURRENT WITHDRAWAL TEST
        # =========================================

        print("\nCONCURRENT WITHDRAWAL TEST")

        # Create a separate account.
        concurrent_account_response = client.post(
            "/api/accounts",
            json={
                "account_name": "Concurrent Test Account",
            },
            headers=headers,
        )

        concurrent_account_data = check_response(
            concurrent_account_response,
            201,
            "CREATE CONCURRENT TEST ACCOUNT",
        )

        concurrent_account_id = (
            concurrent_account_data["account"]["id"]
        )

        # Deposit ₹100.
        concurrent_deposit_response = client.post(
            "/api/transactions/deposit",
            json={
                "account_id": concurrent_account_id,
                "amount_paise": 10000,
                "description": "Concurrency test deposit",
            },
            headers={
                **headers,
                "Idempotency-Key": f"concurrent-deposit-{unique_id}",
            },
        )

        check_response(
            concurrent_deposit_response,
            201,
            "DEPOSIT ₹100 FOR CONCURRENCY TEST",
        )

        # Synchronize both requests before sending.
        barrier = Barrier(2)

        def concurrent_withdrawal(key):
            barrier.wait()

            with app.test_client() as thread_client:
                response = thread_client.post(
                    "/api/transactions/withdraw",
                    json={
                        "account_id": concurrent_account_id,
                        "amount_paise": 6000,
                        "description": "Concurrent ₹60 withdrawal",
                    },
                    headers={
                        **headers,
                        "Idempotency-Key": key,
                    },
                )

                return response.status_code, response.get_json()

        with ThreadPoolExecutor(max_workers=2) as executor:

            futures = [
                executor.submit(
                    concurrent_withdrawal,
                    f"concurrent-withdraw-{unique_id}-1",
                ),
                executor.submit(
                    concurrent_withdrawal,
                    f"concurrent-withdraw-{unique_id}-2",
                ),
            ]

            results = [
                future.result()
                for future in futures
            ]

        for index, (status, data) in enumerate(
            results,
            start=1,
        ):
            print(f"\nConcurrent request {index}")
            print("Status:", status)
            print("Response:", data)

        statuses = sorted(
            status for status, data in results
        )

        assert statuses == [201, 400], (
            f"Expected one success and one refusal, got {statuses}"
        )

        # Check final balance.
        concurrent_balance_response = client.get(
            f"/api/accounts/{concurrent_account_id}/balance",
            headers=headers,
        )

        concurrent_balance_data = check_response(
            concurrent_balance_response,
            200,
            "CONCURRENT ACCOUNT FINAL BALANCE",
        )

        assert (
            concurrent_balance_data["balance_paise"] == 4000
        ), "Concurrency test failed: expected ₹40 balance"

        print(
            "PASS: Concurrent withdrawals did not overdraw the account"
        )

        # =========================================
        # FINAL RESULT
        # =========================================

        print("\n================================")
        print("ALL BASIC AND CONCURRENCY CHECKS PASSED")
        print("================================")

        print("First account balance: ₹50")
        print("Second account balance: ₹30")
        print("Deposit replay: No duplicate transaction")
        print("Refused withdrawal: Recorded in statement")
        print("Concurrent withdrawals: No overdraft")


if __name__ == "__main__":
    main()
