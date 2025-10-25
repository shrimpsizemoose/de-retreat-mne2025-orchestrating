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
    """Fetch recent transactions and push to XCom automatically via return."""
    logger.info("📥 Fetching recent transactions...")
    config = Config.load()

    try:
        transactions = fetch_recent_transactions(config)
        logger.info(f"✅ Fetched {len(transactions)} transactions")
        return transactions  # Automatically pushed to XCom
    except APIError as e:
        logger.error(f"❌ Failed to fetch transactions: {e}")
        raise


def enrich_user_features_func(**context):
    """
    Pull transactions from XCom, enrich with user features.

    TODO: Implement this function!
    """
    logger.info("👥 Enriching with user features...")

    # TODO: Pull transactions from previous task using XCom
    # HINT: task_instance = context["task_instance"]
    # HINT: transactions = task_instance.xcom_pull(task_ids="fetch_transactions")

    # TODO: Get config
    # HINT: config = Config.load()

    # TODO: Extract unique user_ids from transactions

    # TODO: Loop through users and fetch features
    # HINT: Use fetch_user_features(config, user_id)
    # HINT: Handle errors with try/except - use DEFAULT_USER_FEATURES on failure

    # TODO: Return user_features dict

    raise NotImplementedError("TODO: Implement enrich_user_features_func")


def enrich_merchant_risk_func(**context):
    """
    Pull transactions from XCom, enrich with merchant risks.

    TODO: Implement this function!
    """
    logger.info("🏪 Enriching with merchant risk scores...")

    # TODO: Pull transactions from XCom (same as enrich_user_features_func)

    # TODO: Get config

    # TODO: Extract unique merchant_ids from transactions

    # TODO: Loop through merchants and fetch risk scores
    # HINT: Use fetch_merchant_risk(config, merchant_id)
    # HINT: This API is FLAKY - expect failures!
    # HINT: Use DEFAULT_MERCHANT_RISK on errors

    # TODO: Return merchant_risks dict

    raise NotImplementedError("TODO: Implement enrich_merchant_risk_func")


def run_inference_func(**context):
    """Run fraud detection model on enriched data."""
    logger.info("🤖 Running fraud detection model...")

    # TODO: Pull data from THREE tasks using XCom:
    # HINT: task_instance = context["task_instance"]
    # HINT: transactions = task_instance.xcom_pull(task_ids="fetch_transactions")
    # HINT: user_features = task_instance.xcom_pull(task_ids="enrich_user_features")
    # HINT: merchant_risks = task_instance.xcom_pull(task_ids="enrich_merchant_risk")

    # TODO: Engineer features using engineer_features()

    # TODO: Load model and predict
    # HINT: model = load_model()
    # HINT: predictions_df = predict_fraud(model, features_df)

    # TODO: Calculate stats (fraud_count, fraud_rate, avg_fraud_prob)

    # TODO: Return dict with predictions and stats
    # HINT: Must be JSON-serializable! Use .to_dict(orient="records")

    raise NotImplementedError("TODO: Implement run_inference_func")


def save_results_func(**context):
    """Save predictions to file."""
    logger.info("💾 Saving predictions...")

    # TODO: Pull result from run_inference task

    # Use results/ directory in phase3_airflow/
    results_dir = Path(__file__).parent.parent / "results"
    results_dir.mkdir(exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    results_file = results_dir / f"predictions_{timestamp}.json"

    # TODO: Save result to JSON file
    # HINT: with open(results_file, "w") as f:
    # HINT:     json.dump(result, f, indent=2)

    logger.info(f"✅ Results saved to {results_file}")


def emit_metrics_func(**context):
    """Emit metrics to Pushgateway."""
    logger.info("📊 Emitting metrics...")

    # TODO: Pull result from run_inference task

    config = Config.load()
    metrics = MetricsCollector(config)

    # TODO: Extract stats from result
    # HINT: stats = result["stats"]

    # TODO: Calculate pipeline duration
    # HINT: execution_date = context["execution_date"]
    # HINT: duration = (datetime.utcnow() - execution_date).total_seconds()

    # TODO: Record metrics using metrics.record_*() methods
    # HINT: metrics.record_fraud_rate(stats["fraud_rate"])
    # HINT: metrics.record_transactions(stats["total_transactions"])
    # HINT: metrics.record_avg_fraud_prob(stats["avg_fraud_probability"])
    # HINT: metrics.record_duration(duration)

    # TODO: Push metrics
    # HINT: metrics.push()

    logger.info("✅ Metrics pushed to Pushgateway")


@dag(
    default_args=default_args,
    description="ML fraud detection pipeline with orchestration",
    schedule_interval="*/2 * * * *",
    catchup=False,
    tags=["ml", "fraud", "workshop"],
)
def fraud_detection_pipeline():
    """
    Define the fraud detection DAG.

    TODO: Create PythonOperators and set up task dependencies!
    """

    # TODO: Create PythonOperators for each function
    # fetch_transactions = PythonOperator(
    #     task_id="fetch_transactions",
    #     python_callable=fetch_transactions_func,
    # )
    # enrich_user = PythonOperator(...)
    # enrich_merchant = ...
    # etc
    # TODO: Create operators for:
    #  - enrich_user_features
    #  - enrich_merchant_risk
    #  - run_inference
    #  - save_results
    #  - emit_metrics

    # TODO: Define task dependencies using >> operator
    # HINT: Dependency structure should be:
    #        fetch_transactions
    #              /        \
    #    enrich_user    enrich_merchant
    #              \        /
    #             run_inference
    #              /        \
    #       save_results  emit_metrics

    pass  # TODO: Remove this and implement!


# Instantiate the DAG
fraud_detection_pipeline_dag = fraud_detection_pipeline()
