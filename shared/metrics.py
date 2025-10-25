from prometheus_client import CollectorRegistry, Counter, Gauge, push_to_gateway

from .config import Config


class MetricsCollector:
    def __init__(self, config: Config):
        self.config = config
        self.registry = CollectorRegistry()

        # Define metrics
        self.fraud_rate = Gauge(
            "fraud_rate",
            "Fraud rate (0.0 to 1.0)",
            ["participant"],
            registry=self.registry,
        )

        self.transactions_processed = Counter(
            "transactions_processed_total",
            "Total transactions processed",
            ["participant"],
            registry=self.registry,
        )

        self.pipeline_duration = Gauge(
            "pipeline_duration_seconds",
            "Pipeline execution duration in seconds",
            ["participant"],
            registry=self.registry,
        )

        self.api_failures = Counter(
            "api_failures_total",
            "API call failures by service",
            ["participant", "service"],
            registry=self.registry,
        )

        self.avg_fraud_probability = Gauge(
            "avg_fraud_probability",
            "Average fraud probability across all transactions",
            ["participant"],
            registry=self.registry,
        )

    def record_fraud_rate(self, rate: float):
        self.fraud_rate.labels(participant=self.config.participant_name).set(rate)

    def record_transactions(self, count: int):
        self.transactions_processed.labels(
            participant=self.config.participant_name
        ).inc(count)

    def record_duration(self, seconds: float):
        self.pipeline_duration.labels(participant=self.config.participant_name).set(
            seconds
        )

    def record_api_failure(self, service: str):
        self.api_failures.labels(
            participant=self.config.participant_name, service=service
        ).inc()

    def record_avg_fraud_prob(self, probability: float):
        self.avg_fraud_probability.labels(participant=self.config.participant_name).set(
            probability
        )

    def push(self):
        """
        Push all metrics to Pushgateway.

        Note: Failures to push metrics should NOT crash the pipeline!
        """
        try:
            push_to_gateway(
                self.config.pushgateway_url,
                job="fraud_pipeline",
                registry=self.registry,
                grouping_key={"participant": self.config.participant_name},
            )
        except Exception as e:
            # TODO: Should we even log this error? How?
            # IMPORTANT: Don't fail the pipeline if metrics push fails!
            print(f"⚠️  Failed to push metrics: {e}")
            # Don't raise - metrics push failure shouldn't stop the pipeline
