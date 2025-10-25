#!/usr/bin/env python3

import logging
import sys
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tasks import run_fraud_pipeline

from shared.config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """
    Setup and run APScheduler to execute fraud pipeline periodically.
    """
    config = Config.load()

    logger.info("🕐 Initializing APScheduler...")
    logger.info(f"👤 Participant: {config.participant_name}")
    logger.info(f"⏱️  Pipeline interval: every {config.pipeline_interval_minutes} minutes")

    # Create scheduler
    scheduler = BlockingScheduler()

    # TODO: Add job to scheduler
    # HINT: Use scheduler.add_job()
    # HINT: Set trigger to CronTrigger with minute interval
    # HINT: Set id and replace_existing for easier debugging
    # HINT: For every 2 minutes use: CronTrigger(minute=f'*/{config.pipeline_interval_minutes}')

    # Add fraud pipeline job
    scheduler.add_job(
        run_fraud_pipeline,
        trigger=CronTrigger(minute=f"*/{config.pipeline_interval_minutes}"),
        id="fraud_detection_pipeline",
        replace_existing=True,
        max_instances=1,  # Prevent overlapping runs
    )

    logger.info("✅ Scheduler configured")
    # logger.info(f"📅 Next run: {scheduler.get_jobs()[0].next_run_time}")
    logger.info("")
    logger.info("🚀 Starting scheduler (Ctrl+C to stop)...")
    logger.info("=" * 60)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("\n" + "=" * 60)
        logger.info("🛑 Scheduler stopped by user")
        scheduler.shutdown()


if __name__ == "__main__":
    main()
