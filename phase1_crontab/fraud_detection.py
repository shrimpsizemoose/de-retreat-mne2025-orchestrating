#!/usr/bin/env python3
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.api_client import (
    DEFAULT_MERCHANT_RISK,
    DEFAULT_USER_FEATURES,
    APIError,
    fetch_merchant_risk,
    fetch_recent_transactions,
    fetch_user_features,
)
from shared.config import Config
from shared.feature_engineering import engineer_features
from shared.metrics import MetricsCollector
from shared.model_loader import load_model, predict_fraud

# Setup logging
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_dir / "fraud_detection.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def main():
    """
    Main pipeline execution.

    Pipeline steps:
    1. Fetch recent transactions
    2. Enrich with user features
    3. Enrich with merchant risk scores (flaky!)
    4. Engineer features
    5. Run fraud detection model
    6. Save predictions
    7. Emit metrics
    """
    start_time = time.time()

    # Load configuration
    config = Config.load()
    metrics = MetricsCollector(config)

    logger.info("=" * 60)
    logger.info("🚀 Starting fraud detection pipeline (crontab)")
    logger.info(f"👤 Participant: {config.participant_name}")
    logger.info("=" * 60)

    try:
        # Step 1: Fetch recent transactions
        logger.info("📥 Fetching recent transactions...")
        try:
            transactions = fetch_recent_transactions(config)
            logger.info(f"✅ Fetched {len(transactions)} transactions")
        except APIError as e:
            logger.error(f"❌ Failed to fetch transactions: {e}")
            metrics.record_api_failure("transactions")
            raise

        if not transactions:
            logger.info("ℹ️ No transactions to process")
            metrics.record_duration(time.time() - start_time)
            metrics.push()
            return

        # Step 2: Fetch user features for each transaction
        logger.info("👥 Fetching user features...")
        user_features = {}

        # TODO: Loop through transactions and fetch user features
        # HINT: Extract unique user_ids first to avoid duplicate calls
        # HINT: Use fetch_user_features(config, user_id)
        # HINT: Store results in user_features dict: user_features[user_id] = result
        # HINT: Count API failures and record them with metrics.record_api_failure("users")

        # Example starter code:
        unique_user_ids = set(t["user_id"] for t in transactions)
        user_api_failures = 0

        for user_id in unique_user_ids:
            try:
                user_features[user_id] = fetch_user_features(config, user_id)
            except APIError as e:
                logger.warning(f"Не получилось с {user_id}: {e}")
                user_api_failures += 1
                metrics.record_api_failure("user")

        logger.info(
            f"✅ Fetched features for {len(user_features)} users ({user_api_failures} failures)"
        )

        # Step 3: Fetch merchant risk scores (FLAKY API!)
        logger.info("🏪 Fetching merchant risk scores...")
        merchant_risks = {}

        # Example starter code:
        unique_merchant_ids = set(t["merchant_id"] for t in transactions)
        merchant_api_failures = 0

        for merchant_id in unique_merchant_ids:
            try:
                merchant_risks[merchant_id] = fetch_merchant_risk(config, merchant_id)
            except APIError as e:
                logger.warning(f"Не получилось с {merchant_id}: {e}")
                merchant_api_failures += 1
                metrics.record_api_failure("merchants")

        logger.info(
            f"✅ Fetched risk scores for {len(merchant_risks)} merchants ({merchant_api_failures} failures)"
        )

        # Step 4: Engineer features
        logger.info("⚙️  Engineering features...")
        features_df = engineer_features(transactions, user_features, merchant_risks)
        logger.info(f"✅ Engineered {len(features_df)} feature rows")

        # Step 5: Load model and make predictions
        logger.info("🤖 Running fraud detection model...")
        model = load_model()
        predictions_df = predict_fraud(model, features_df)
        logger.info(f"✅ Generated {len(predictions_df)} predictions")

        # Step 6: Save results
        logger.info("💾 Saving predictions...")

        results_dir = Path(__file__).parent / "results"
        results_dir.mkdir(exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        results_file = results_dir / f"predictions_{timestamp}.json"

        results = {
            "timestamp": timestamp,
            "total_transactions": len(transactions),
            "predictions": predictions_df.to_dict(orient="records"),
        }

        with open(results_file, "w") as fp:
            json.dump(results, fp, indent=2)

        logger.info(f"✅ Results saved to {results_file}")

        # Step 7: Calculate and emit metrics
        logger.info("📊 Calculating metrics...")

        fraud_count = predictions_df["is_fraud"].sum()
        fraud_rate = fraud_count / len(predictions_df)
        # по-хорошему тут надо бы хэндлить ситуацию деления на ноль

        avg_fraud_prob = predictions_df["fraud_probability"].mean()

        # Record metrics
        metrics.record_fraud_rate(fraud_rate)
        metrics.record_transactions(len(transactions))
        metrics.record_avg_fraud_prob(avg_fraud_prob)
        metrics.record_duration(time.time() - start_time)

        # Push metrics to Pushgateway
        logger.info("📤 Pushing metrics to Pushgateway...")
        metrics.push()
        logger.info("✅ Metrics pushed successfully")

        # Summary
        duration = time.time() - start_time
        logger.info("=" * 60)
        logger.info(f"✨ Pipeline completed successfully in {duration:.2f}s")
        logger.info(f"   Transactions: {len(transactions)}")
        logger.info(f"   Fraud detected: {predictions_df['is_fraud'].sum()} ({fraud_rate:.1%})")
        logger.info(f"   Avg fraud probability: {avg_fraud_prob:.3f}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"💥 Pipeline failed: {e}", exc_info=True)

        # TODO: Should we emit failure metrics even on error?
        # HINT: Yes! Emit what we can so we can see failures in Grafana
        try:
            metrics.record_duration(time.time() - start_time)
            metrics.push()
        except:
            pass  # NB! Don't fail on metrics push failure

        sys.exit(1)


if __name__ == "__main__":
    main()
