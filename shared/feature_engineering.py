import pandas as pd


def engineer_features(
    transactions: list[dict],
    user_features: dict[str, dict],
    merchant_risks: dict[str, dict],
) -> pd.DataFrame:
    """
    Transform raw transaction data into model features.

    Args:
        transactions: list of transaction dicts from API
        user_features: dict mapping user_id -> user features dict
        merchant_risks: dict mapping merchant_id -> merchant risk dict

    Returns:
        DataFrame with engineered features ready for model
    """
    if not transactions:
        # Return empty DataFrame with correct schema
        return pd.DataFrame(
            columns=[
                "transaction_id",
                "amount",
                "payment_method_encoded",
                "device_type_encoded",
                "hour_of_day",
                "is_weekend",
                "account_age_days",
                "total_transactions",
                "avg_transaction_amount",
                "failed_transactions_last_30d",
                "account_verified",
                "merchant_risk_score",
                "merchant_dispute_rate",
            ]
        )

    df = pd.DataFrame(transactions)

    # temporal features
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["hour_of_day"] = df["timestamp"].dt.hour
    df["is_weekend"] = (df["timestamp"].dt.dayofweek >= 5).astype(int)

    payment_encoding = {"credit_card": 0, "debit": 1, "paypal": 2, "crypto": 3}
    df["payment_method_encoded"] = (
        df["payment_method"].map(payment_encoding).fillna(0).astype(int)
    )

    # Encode device type
    device_encoding = {"desktop": 0, "mobile": 1, "tablet": 2}
    df["device_type_encoded"] = (
        df["device_type"].map(device_encoding).fillna(0).astype(int)
    )

    # Join user features
    df["account_age_days"] = df["user_id"].map(
        lambda uid: user_features.get(uid, {}).get("account_age_days", 0)
    )
    df["total_transactions"] = df["user_id"].map(
        lambda uid: user_features.get(uid, {}).get("total_transactions", 0)
    )
    df["avg_transaction_amount"] = df["user_id"].map(
        lambda uid: user_features.get(uid, {}).get("avg_transaction_amount", 50.0)
    )
    df["failed_transactions_last_30d"] = df["user_id"].map(
        lambda uid: user_features.get(uid, {}).get("failed_transactions_last_30d", 0)
    )
    df["account_verified"] = df["user_id"].map(
        lambda uid: 1
        if user_features.get(uid, {}).get("account_status", "unverified") == "verified"
        else 0
    )

    # Join merchant features
    df["merchant_risk_score"] = df["merchant_id"].map(
        lambda mid: merchant_risks.get(mid, {}).get("risk_score", 0.5)
    )
    df["merchant_dispute_rate"] = df["merchant_id"].map(
        lambda mid: merchant_risks.get(mid, {}).get("dispute_rate", 0.0)
    )

    # Select only features needed by model (in correct order)
    feature_columns = [
        "amount",
        "payment_method_encoded",
        "device_type_encoded",
        "hour_of_day",
        "is_weekend",
        "account_age_days",
        "total_transactions",
        "avg_transaction_amount",
        "failed_transactions_last_30d",
        "account_verified",
        "merchant_risk_score",
        "merchant_dispute_rate",
    ]

    return df[["transaction_id", *feature_columns]]
