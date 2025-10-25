import requests

from .config import Config


class APIError(Exception):
    """Raised when API calls fail."""

    pass


# Default values for when APIs fail
DEFAULT_USER_FEATURES = {
    "account_age_days": 0,
    "total_transactions": 0,
    "avg_transaction_amount": 50.0,
    "failed_transactions_last_30d": 0,
    "account_status": "unverified",
}

DEFAULT_MERCHANT_RISK = {
    "risk_score": 0.5,
    "dispute_rate": 0.0,
    "status": "unknown",
}


def fetch_recent_transactions(config: Config, minutes: int | None = None) -> list[dict]:
    """
    Fetch recent transactions from the API.

    Args:
        config: Configuration object
        minutes: Time window for recent transactions (uses config default if not specified)

    Returns:
        List of transaction dictionaries

    Raises:
        APIError: If the API call fails
    """
    if minutes is None:
        minutes = config.fetch_window_minutes

    url = f"{config.api_base_url}/api/transactions/recent"
    params = {"minutes": minutes}

    # TODO: Implement error handling for:
    #       - Network timeouts
    #       - 503 Service Unavailable
    #       - 429 Rate limiting
    #       - Empty responses
    # HINT: Use try/except with requests.exceptions
    # HINT: Use timeout parameter in requests.get()

    try:
        response = requests.get(url, params=params, timeout=config.api_timeout)
        response.raise_for_status()
        data = response.json()
        return data.get("transactions", [])
    except requests.Timeout:
        raise APIError(f"Timeout fetching transactions from {url}")
    except requests.RequestException as e:
        raise APIError(f"Failed to fetch transactions: {e}")


def fetch_user_features(config: Config, user_id: str) -> dict:
    """
    Fetch user features for a given user ID.

    Args:
        config: Configuration object
        user_id: The user ID to fetch features for

    Returns:
        User features dict, or default values if user not found

    Note:
        Returns default values for new users (404) instead of raising an error.
    """
    url = f"{config.api_base_url}/api/users/{user_id}"

    # TODO: Implement error handling for:
    #       - 404 Not Found (new users) - return DEFAULT_USER_FEATURES
    #       - Network timeouts
    #       - Other HTTP errors
    # HINT: Check response.status_code == 404 specifically

    try:
        response = requests.get(url, timeout=config.api_timeout)
        if response.status_code == 404:
            # New user - return defaults
            return DEFAULT_USER_FEATURES
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        # On timeout, return defaults to keep pipeline running
        return DEFAULT_USER_FEATURES
    except requests.RequestException:
        return DEFAULT_USER_FEATURES


def fetch_merchant_risk(config: Config, merchant_id: str) -> dict:
    """
    Fetch merchant risk score.

    THIS IS THE FLAKY API - expect timeouts and errors!

    Args:
        config: Configuration object
        merchant_id: The merchant ID to fetch risk for

    Returns:
        Merchant risk dict, or default values if call fails

    Note:
        This API is intentionally unreliable. Use default risk scores on failure.
    """
    url = f"{config.api_base_url}/api/merchant-risk/{merchant_id}"

    # TODO: Implement robust error handling for:
    #       - Timeouts (common!) - return DEFAULT_MERCHANT_RISK
    #       - 500 Internal Server Error - return DEFAULT_MERCHANT_RISK
    #       - 408 Request Timeout - return DEFAULT_MERCHANT_RISK
    #       - 404 Not Found - return DEFAULT_MERCHANT_RISK
    # HINT: This API is intentionally flaky - failures are expected!
    # HINT: Use a shorter timeout (e.g., 5 seconds) for this endpoint

    try:
        response = requests.get(url, timeout=5)  # Shorter timeout for flaky API
        if response.status_code in [404, 408, 500, 503]:
            return DEFAULT_MERCHANT_RISK
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        # Expected for this flaky API
        return DEFAULT_MERCHANT_RISK
    except requests.RequestException:
        return DEFAULT_MERCHANT_RISK
