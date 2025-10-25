import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Config:
    """Workshop configuration loaded from environment variables."""

    # API Configuration
    api_base_url: str
    pushgateway_url: str
    api_timeout: int

    # Pipeline Configuration
    pipeline_interval_minutes: int
    fetch_window_minutes: int

    participant_name: str
    log_level: str

    @classmethod
    def load(cls):
        load_dotenv()

        return cls(
            api_base_url=os.getenv(
                "API_BASE_URL", "https://api.de-retreat.mock.events"
            ),
            pushgateway_url=os.getenv(
                "PUSHGATEWAY_URL", "https://metrics.de-retreat.mock.events"
            ),
            api_timeout=int(os.getenv("API_TIMEOUT", "10")),
            pipeline_interval_minutes=int(os.getenv("PIPELINE_INTERVAL_MINUTES", "2")),
            fetch_window_minutes=int(os.getenv("FETCH_WINDOW_MINUTES", "2")),
            participant_name=os.getenv("PARTICIPANT_NAME", "anonymous"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
