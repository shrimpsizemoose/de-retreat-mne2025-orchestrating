#!/usr/bin/env python3

import sys
from pathlib import Path

# add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.api_client import (
    APIError,
    fetch_merchant_risk,
    fetch_recent_transactions,
    fetch_user_features,
)
from shared.config import Config


def test_transactions_endpoint(config: Config) -> bool:
    """Test /api/transactions/recent endpoint."""
    print("\n" + "=" * 60)
    print("🔍 Testing transactions endpoint...")
    print(f"   URL: {config.api_base_url}/api/transactions/recent")

    try:
        transactions = fetch_recent_transactions(config, minutes=5)
        print(f"✅ SUCCESS: Fetched {len(transactions)} transactions")

        if transactions:
            print(
                f"   Sample transaction: {transactions[0].get('transaction_id', 'N/A')}"
            )

        return True

    except APIError as e:
        print(f"❌ FAILED: {e}")
        return False


def test_users_endpoint(config: Config) -> bool:
    """Test /api/users/{user_id} endpoint."""
    print("\n" + "=" * 60)
    print("🔍 Testing users endpoint...")
    print(f"   URL: {config.api_base_url}/api/users/{{user_id}}")

    # Try with a sample user ID
    test_user_id = "user_test123"

    try:
        features = fetch_user_features(config, test_user_id)
        print("✅ SUCCESS: Fetched user features")
        print("   User status:", features.get("account_status", "N/A"))
        print("   Account age:", features.get("account_age_days", "N/A"), "days")

        return True

    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_merchant_risk_endpoint(config: Config) -> bool:
    """Test /api/merchant-risk/{merchant_id} endpoint."""
    print("\n" + "=" * 60)
    print("🔍 Testing merchant risk endpoint (FLAKY API)...")
    print(f"   URL: {config.api_base_url}/api/merchant-risk/{{merchant_id}}")

    test_merchant_id = "merch_test456"

    try:
        risk = fetch_merchant_risk(config, test_merchant_id)
        print("✅ SUCCESS: Fetched merchant risk")
        print("   Risk score:", risk.get("risk_score", "N/A"))
        print("   Status:", risk.get("status", "N/A"))

        return True

    except Exception as e:
        print("⚠️  EXPECTED BEHAVIOR:", e)
        print("   This API is flaky - failures are normal!")
        return True


def test_pushgateway(config: Config) -> bool:
    """Test Pushgateway connection."""
    print("\n" + "=" * 60)
    print("🔍 Testing Pushgateway...")
    print(f"   URL: {config.pushgateway_url}")

    from shared.metrics import MetricsCollector

    try:
        metrics = MetricsCollector(config)
        metrics.record_fraud_rate(0.05)
        metrics.push()

        print("✅ SUCCESS: Pushed test metrics to Pushgateway")
        print("   Check Grafana to see your metrics!")

        return True

    except Exception as e:
        print("❌ FAILED:", e)
        return False


def main():
    print("=" * 60)
    print("🧪 API Connection Test")
    print("=" * 60)

    config = Config.load()

    print("\n📋 Configuration:")
    print("   Participant:", config.participant_name)
    print("   API Base URL:", config.api_base_url)
    print("   Pushgateway URL:", config.pushgateway_url)

    results = {
        "Transactions API": test_transactions_endpoint(config),
        "Users API": test_users_endpoint(config),
        "Merchant Risk API": test_merchant_risk_endpoint(config),
        "Pushgateway": test_pushgateway(config),
    }

    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
        all_passed = all_passed and passed

    print("=" * 60)

    if not all_passed:
        print("\n⚠️  Some tests failed. Please check your configuration.")
        print("   - Verify API_BASE_URL in .env")
        print("   - Verify PUSHGATEWAY_URL in .env")
        print("   - Check that instructor's services are running")
        return 1

    print("\n🎉 All tests passed! You're ready to start the workshop.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
