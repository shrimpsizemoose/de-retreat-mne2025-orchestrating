import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.results import Results
from dramatiq.results.backends import RedisBackend

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
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Setup Dramatiq broker with Redis
redis_broker = RedisBroker(host="localhost", port=6379)
result_backend = RedisBackend(host="localhost", port=6379)
redis_broker.add_middleware(Results(backend=result_backend))
dramatiq.set_broker(redis_broker)


@dramatiq.actor(max_retries=3, min_backoff=1000, max_backoff=30000, store_results=True)
def fetch_transactions_task(fetch_window_minutes: int = 2) -> list[dict]:
    """
    Fetch recent transactions from API.

    Retry config: 3 retries, 1s to 30s exponential backoff
    """
    logger.info(f"📥 Fetching transactions for last {fetch_window_minutes} minutes...")

    config = Config.load()

    try:
        transactions = fetch_recent_transactions(config, minutes=fetch_window_minutes)
        logger.info(f"✅ Fetched {len(transactions)} transactions")
        return transactions
    except APIError as e:
        logger.error(f"❌ Failed to fetch transactions: {e}")
        raise  # Dramatiq will retry automatically


@dramatiq.actor(max_retries=5, min_backoff=500, max_backoff=10000, store_results=True)
def enrich_user_features_task(transactions: list[dict]) -> dict[str, dict]:
    """
    Enrich transactions with user features.

    Retry config: 5 retries, 500ms to 10s exponential backoff
    Higher retries because individual user lookups might fail.
    """
    logger.info(f"👥 Enriching {len(transactions)} transactions with user features...")

    config = Config.load()
    user_features = {}

    # TODO: Implement user feature fetching
    # HINT: Extract unique user_ids from transactions
    # HINT: Loop through and call fetch_user_features(config, user_id)
    # HINT: Store in user_features dict
    # HINT: Handle failures gracefully - use DEFAULT_USER_FEATURES

    unique_user_ids = set(t["user_id"] for t in transactions)
    failures = 0

    for user_id in unique_user_ids:
        # TODO: Fetch user features with error handling
        # HINT: fetch_user_features already returns defaults on 404/timeout
        try:
            features = fetch_user_features(config, user_id)
            user_features[user_id] = features
        except Exception as e:
            logger.warning(f"Failed to fetch user {user_id}: {e}")
            user_features[user_id] = DEFAULT_USER_FEATURES
            failures += 1

    logger.info(
        f"✅ Fetched features for {len(user_features)} users ({failures} failures)"
    )
    return user_features


@dramatiq.actor(
    max_retries=5,
    min_backoff=2000,
    max_backoff=30000,
    store_results=True,
    time_limit=120000,
)
def enrich_merchant_risk_task(transactions: list[dict]) -> dict[str, dict]:
    """
    Enrich transactions with merchant risk scores.

    THIS IS THE FLAKY API - implement retries with backoff

    Retry config: 5 retries, 2s to 30s exponential backoff
    Time limit: 2 minutes (this API is slow)
    """
    logger.info(
        f"🏪 Enriching {len(transactions)} transactions with merchant risk scores..."
    )

    config = Config.load()
    merchant_risks = {}

    # TODO: Implement merchant risk fetching
    # HINT: Extract unique merchant_ids from transactions
    # HINT: Loop through and call fetch_merchant_risk(config, merchant_id)
    # HINT: This API is FLAKY - expect failures!
    # HINT: Use DEFAULT_MERCHANT_RISK on failures
    # HINT: fetch_merchant_risk already returns defaults on error

    unique_merchant_ids = set(t["merchant_id"] for t in transactions)
    failures = 0

    for merchant_id in unique_merchant_ids:
        # TODO: Fetch merchant risk with error handling
        try:
            risk = fetch_merchant_risk(config, merchant_id)
            merchant_risks[merchant_id] = risk
        except Exception as e:
            logger.warning(f"Failed to fetch merchant {merchant_id}: {e}")
            merchant_risks[merchant_id] = DEFAULT_MERCHANT_RISK
            failures += 1

    logger.info(
        f"✅ Fetched risk scores for {len(merchant_risks)} merchants ({failures} failures)"
    )
    return merchant_risks


@dramatiq.actor(store_results=True)
def run_inference_task(
    transactions: list[dict],
    user_features: dict[str, dict],
    merchant_risks: dict[str, dict],
) -> dict:
    """
    Run fraud detection model on enriched data.

    No retries needed - this is deterministic.
    """
    logger.info(f"🤖 Running fraud detection on {len(transactions)} transactions...")

    # Engineer features
    features_df = engineer_features(transactions, user_features, merchant_risks)
    logger.info(f"⚙️  Engineered {len(features_df)} feature rows")

    # Load model and predict
    model = load_model()
    predictions_df = predict_fraud(model, features_df)
    logger.info(f"✅ Generated {len(predictions_df)} predictions")

    # Convert to dict for serialization
    predictions = predictions_df.to_dict(orient="records")

    # Calculate stats
    fraud_count = predictions_df["is_fraud"].sum()
    fraud_rate = fraud_count / len(predictions_df) if len(predictions_df) > 0 else 0.0
    avg_fraud_prob = predictions_df["fraud_probability"].mean()

    result = {
        "predictions": predictions,
        "stats": {
            "total_transactions": len(transactions),
            "fraud_count": int(fraud_count),
            "fraud_rate": float(fraud_rate),
            "avg_fraud_probability": float(avg_fraud_prob),
        },
    }

    logger.info(
        f"📊 Fraud rate: {fraud_rate:.1%}, Avg probability: {avg_fraud_prob:.3f}"
    )

    return result


@dramatiq.actor
def save_results_task(result: dict) -> str:
    """
    Save predictions to file.

    No retries needed - this is a local operation.
    """
    logger.info("💾 Saving predictions...")

    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    results_file = results_dir / f"predictions_{timestamp}.json"

    with open(results_file, "w") as f:
        json.dump(result, f, indent=2)

    logger.info(f"✅ Results saved to {results_file}")
    return str(results_file)


@dramatiq.actor
def emit_metrics_task(result: dict, duration: float):
    """
    Calculate and push metrics to Pushgateway.

    If metrics push fails, log but don't crash the pipeline.
    """
    logger.info("📊 Emitting metrics...")

    config = Config.load()
    metrics = MetricsCollector(config)

    stats = result["stats"]

    # Record metrics
    metrics.record_fraud_rate(stats["fraud_rate"])
    metrics.record_transactions(stats["total_transactions"])
    metrics.record_avg_fraud_prob(stats["avg_fraud_probability"])
    metrics.record_duration(duration)

    # Push to Pushgateway
    metrics.push()
    logger.info("✅ Metrics pushed to Pushgateway")


def run_fraud_pipeline():
    """
    Orchestrate the entire fraud detection pipeline.

    This chains all tasks together in sequence:
    1. Fetch transactions
    2. Enrich with user features (parallel)
    3. Enrich with merchant risks (parallel)
    4. Run inference
    5. Save results
    6. Emit metrics
    """
    start_time = time.time()
    config = Config.load()

    logger.info("=" * 60)
    logger.info(f"🚀 Starting fraud detection pipeline (Dramatiq)")
    logger.info(f"👤 Participant: {config.participant_name}")
    logger.info("=" * 60)

    try:
        # TODO: Orchestrate task execution
        # HINT: Use .send() to enqueue tasks
        # HINT: Use .get_result(block=True, timeout=60000) to wait for results
        # HINT: Chain tasks: fetch → enrich → inference → save → metrics

        # Step 1: Fetch transactions
        logger.info("Step 1: Fetching transactions...")
        transactions_message = fetch_transactions_task.send(config.fetch_window_minutes)
        transactions = transactions_message.get_result(block=True, timeout=60000)

        if not transactions:
            logger.info("ℹ️  No transactions to process")
            return

        # Step 2 & 3: Enrich with user features and merchant risks (can run in parallel!)
        logger.info("Step 2-3: Enriching with user and merchant data...")

        # TODO: Send both enrichment tasks in parallel
        # HINT: Send both tasks, then get both results
        user_msg = enrich_user_features_task.send(transactions)
        merchant_msg = enrich_merchant_risk_task.send(transactions)

        # Wait for both to complete
        user_features = user_msg.get_result(block=True, timeout=120000)
        merchant_risks = merchant_msg.get_result(block=True, timeout=120000)

        # Step 4: Run inference
        logger.info("Step 4: Running inference...")
        inference_msg = run_inference_task.send(
            transactions, user_features, merchant_risks
        )
        result = inference_msg.get_result(block=True, timeout=60000)

        # Step 5: Save results
        logger.info("Step 5: Saving results...")
        save_msg = save_results_task.send(result)
        save_msg.get_result(block=True, timeout=30000)

        # Step 6: Emit metrics
        duration = time.time() - start_time
        logger.info("Step 6: Emitting metrics...")
        emit_metrics_task.send(result, duration)

        # Summary
        stats = result["stats"]
        logger.info("=" * 60)
        logger.info(f"✨ Pipeline completed successfully in {duration:.2f}s")
        logger.info(f"   Transactions: {stats['total_transactions']}")
        logger.info(
            f"   Fraud detected: {stats['fraud_count']} ({stats['fraud_rate']:.1%})"
        )
        logger.info(f"   Avg fraud probability: {stats['avg_fraud_probability']:.3f}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"💥 Pipeline failed: {e}", exc_info=True)
        raise
