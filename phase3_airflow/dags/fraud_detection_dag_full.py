import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow.decorators import dag
from airflow.operators.python import PythonOperator

# Add paths for imports (shared utilities and model)
# Go up from dags/ to phase3_airflow/ to workshop-repo/
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root))

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

logger = logging.getLogger(__name__)


# DAG default arguments
default_args = {
    "owner": "fraud_team",
    "depends_on_past": False,
    "start_date": datetime(2025, 1, 25),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(seconds=30),
    "execution_timeout": timedelta(minutes=10),
}


def fetch_transactions_func(**context):
    """
    Fetch recent transactions and push to XCom.

    Returns:
        List of transaction dicts
    """
    logger.info("📥 Fetching recent transactions...")

    config = Config.load()

    try:
        transactions = fetch_recent_transactions(config)
        logger.info(f"✅ Fetched {len(transactions)} transactions")
        return transactions

    except APIError as e:
        logger.error(f"❌ Failed to fetch transactions: {e}")
        raise


def enrich_user_features_func(**context):
    """
    Pull transactions from XCom, enrich with user features, push back.

    Returns:
        Dict mapping user_id -> user features
    """
    logger.info("👥 Enriching with user features...")

    task_instance = context["task_instance"]
    transactions = task_instance.xcom_pull(task_ids="fetch_transactions")

    config = Config.load()
    user_features = {}

    unique_user_ids = set(t["user_id"] for t in transactions)
    failures = 0

    for user_id in unique_user_ids:
        try:
            features = fetch_user_features(config, user_id)
            user_features[user_id] = features
        except Exception as e:
            logger.warning(f"Failed to fetch user {user_id}: {e}")
            user_features[user_id] = DEFAULT_USER_FEATURES
            failures += 1

    logger.info(f"✅ Fetched features for {len(user_features)} users ({failures} failures)")

    return user_features


def enrich_merchant_risk_func(**context):
    """
    Pull transactions from XCom, enrich with merchant risks, push back.

    Returns:
        Dict mapping merchant_id -> merchant risk
    """
    logger.info("🏪 Enriching with merchant risk scores...")

    task_instance = context["task_instance"]
    transactions = task_instance.xcom_pull(task_ids="fetch_transactions")

    config = Config.load()
    merchant_risks = {}

    unique_merchant_ids = set(t["merchant_id"] for t in transactions)
    failures = 0

    for merchant_id in unique_merchant_ids:
        try:
            risk = fetch_merchant_risk(config, merchant_id)
            merchant_risks[merchant_id] = risk
        except Exception as e:
            logger.warning(f"Failed to fetch merchant {merchant_id}: {e}")
            merchant_risks[merchant_id] = DEFAULT_MERCHANT_RISK
            failures += 1

    logger.info(f"✅ Fetched risk scores for {len(merchant_risks)} merchants ({failures} failures)")

    return merchant_risks


def run_inference_func(**context):
    """
    Pull enriched data from XCom, run model, push predictions.

    Returns:
        Dict with predictions and stats
    """
    logger.info("🤖 Running fraud detection model...")

    task_instance = context["task_instance"]
    transactions = task_instance.xcom_pull(task_ids="fetch_transactions")
    user_features = task_instance.xcom_pull(task_ids="enrich_user_features")
    merchant_risks = task_instance.xcom_pull(task_ids="enrich_merchant_risk")

    # Engineer features
    features_df = engineer_features(transactions, user_features, merchant_risks)
    logger.info(f"⚙️  Engineered {len(features_df)} feature rows")

    # Load model and predict
    model = load_model()
    predictions_df = predict_fraud(model, features_df)
    logger.info(f"✅ Generated {len(predictions_df)} predictions")

    # Calculate stats
    fraud_count = predictions_df["is_fraud"].sum()
    fraud_rate = fraud_count / len(predictions_df) if len(predictions_df) > 0 else 0.0
    avg_fraud_prob = predictions_df["fraud_probability"].mean()

    result = {
        "predictions": predictions_df.to_dict(orient="records"),
        "stats": {
            "total_transactions": len(transactions),
            "fraud_count": int(fraud_count),
            "fraud_rate": float(fraud_rate),
            "avg_fraud_probability": float(avg_fraud_prob),
        },
    }

    logger.info(f"📊 Fraud rate: {fraud_rate:.1%}, Avg probability: {avg_fraud_prob:.3f}")

    return result


def save_results_func(**context):
    """
    Pull predictions from XCom and save to file.
    """
    logger.info("💾 Saving predictions...")

    # TODO: Pull predictions from run_inference task
    task_instance = context["task_instance"]
    result = task_instance.xcom_pull(task_ids="run_inference")

    results_dir = Path("/opt/airflow/results")
    results_dir.mkdir(exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    results_file = results_dir / f"predictions_{timestamp}.json"

    with open(results_file, "w") as f:
        json.dump(result, f, indent=2)

    logger.info(f"✅ Results saved to {results_file}")


def emit_metrics_func(**context):
    """
    Pull results from XCom and emit metrics to Pushgateway.
    """
    logger.info("📊 Emitting metrics...")

    # TODO: Pull results from run_inference task
    task_instance = context["task_instance"]
    result = task_instance.xcom_pull(task_ids="run_inference")

    config = Config.load()
    metrics = MetricsCollector(config)

    stats = result["stats"]

    # Calculate pipeline duration from DAG run start
    context["dag_run"]
    execution_date = context["execution_date"]
    duration = (datetime.utcnow() - execution_date).total_seconds()

    # Record metrics
    metrics.record_fraud_rate(stats["fraud_rate"])
    metrics.record_transactions(stats["total_transactions"])
    metrics.record_avg_fraud_prob(stats["avg_fraud_probability"])
    metrics.record_duration(duration)

    # Push to Pushgateway
    metrics.push()
    logger.info("✅ Metrics pushed to Pushgateway")


@dag(
    default_args=default_args,
    description="ML fraud detection pipeline with orchestration",
    schedule="*/2 * * * *",
    catchup=False,
    tags=["ml", "fraud", "workshop"],
)
def fraud_detection_pipeline_full():
    # Define task operators
    # Use PythonOperator for each function
    # Set task_id, python_callable, and dag parameters

    fetch_transactions = PythonOperator(
        task_id="fetch_transactions",
        python_callable=fetch_transactions_func,
    )

    enrich_user_features = PythonOperator(
        task_id="enrich_user_features",
        python_callable=enrich_user_features_func,
    )

    enrich_merchant_risk = PythonOperator(
        task_id="enrich_merchant_risk",
        python_callable=enrich_merchant_risk_func,
    )

    run_inference = PythonOperator(
        task_id="run_inference",
        python_callable=run_inference_func,
    )

    save_results = PythonOperator(
        task_id="save_results",
        python_callable=save_results_func,
    )

    emit_metrics = PythonOperator(
        task_id="emit_metrics",
        python_callable=emit_metrics_func,
    )

    # Define task dependencies
    # Using >> operator to chain tasks
    # Enrichment tasks can run in parallel after fetch_transactions
    # run_inference depends on both enrichment tasks completing

    # Example dependency structure:
    #        fetch_transactions
    #              /        \
    #    enrich_user    enrich_merchant
    #              \        /
    #             run_inference
    #              /        \
    #       save_results  emit_metrics

    (
        fetch_transactions
        >> [enrich_user_features, enrich_merchant_risk]
        >> run_inference
        >> [save_results, emit_metrics]
    )


_ = fraud_detection_pipeline_full()
