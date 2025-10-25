import pickle
from pathlib import Path

import numpy as np
import pandas as pd


def load_model():
    """
    Load the pre-trained fraud detection model.

    Also, pickle sucks, don't use it in real prod systems

    Returns:
        Loaded model object

    Raises:
        FileNotFoundError: If model file doesn't exist
    """
    model_path = Path(__file__).parent.parent / "model" / "fraud_detector.pkl"

    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")

    with open(model_path, "rb") as f:
        model = pickle.load(f)

    return model


def predict_fraud(model, features_df: pd.DataFrame) -> pd.DataFrame:
    """
    Run fraud detection on engineered features.

    Args:
        model: Loaded fraud detection model
        features_df: DataFrame with engineered features (from feature_engineering.py)

    Returns:
        DataFrame with columns:
            - transaction_id: Transaction identifier
            - fraud_probability: Probability of fraud (0.0 to 1.0)
            - is_fraud: Binary prediction (0 or 1)
    """
    if len(features_df) == 0:
        return pd.DataFrame(columns=["transaction_id", "fraud_probability", "is_fraud"])

    # Extract transaction IDs
    transaction_ids = features_df["transaction_id"].values

    # Get feature columns (exclude transaction_id)
    feature_columns = [col for col in features_df.columns if col != "transaction_id"]
    X = features_df[feature_columns]

    probabilities = model.predict_proba(X)
    # model returns [prob_not_fraud, prob_fraud] for each row, we need only fraud prob column
    fraud_probabilities = probabilities[:, 1]

    # Binary predictions (threshold at 0.5)
    predictions = (fraud_probabilities >= 0.5).astype(int)

    # Combine results
    results = pd.DataFrame(
        {
            "transaction_id": transaction_ids,
            "fraud_probability": fraud_probabilities,
            "is_fraud": predictions,
        }
    )

    return results
