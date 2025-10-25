#!/usr/bin/env python3

import pickle
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split


def generate_synthetic_data(n_samples=10000):
    np.random.seed(42)

    # Generate features
    amount = np.random.exponential(100, n_samples)
    payment_method = np.random.randint(0, 3, n_samples)
    device_type = np.random.randint(0, 3, n_samples)
    hour_of_day = np.random.randint(0, 24, n_samples)
    is_weekend = np.random.randint(0, 2, n_samples)
    account_age_days = np.random.exponential(365, n_samples)
    total_transactions = np.random.poisson(50, n_samples)
    avg_transaction_amount = np.random.exponential(80, n_samples)
    failed_transactions_last_30d = np.random.poisson(2, n_samples)
    account_verified = np.random.randint(0, 2, n_samples)
    merchant_risk_score = np.random.beta(2, 5, n_samples)
    merchant_dispute_rate = np.random.beta(1, 20, n_samples)

    # Create fraud labels based on simple rules
    fraud_score = (
        (amount > 500) * 0.3
        + (hour_of_day < 6) * 0.2
        + (hour_of_day > 22) * 0.2
        + (account_age_days < 30) * 0.25
        + (failed_transactions_last_30d > 3) * 0.2
        + (account_verified == 0) * 0.15
        + (merchant_risk_score > 0.6) * 0.3
        + (merchant_dispute_rate > 0.1) * 0.2
    )

    # Add noise and threshold
    fraud_score += np.random.normal(0, 0.1, n_samples)
    is_fraud = (fraud_score > 0.7).astype(int)

    # Combine into feature matrix
    X = np.column_stack(
        [
            amount,
            payment_method,
            device_type,
            hour_of_day,
            is_weekend,
            account_age_days,
            total_transactions,
            avg_transaction_amount,
            failed_transactions_last_30d,
            account_verified,
            merchant_risk_score,
            merchant_dispute_rate,
        ]
    )

    return X, is_fraud


def main():
    print("🔨 Generating synthetic training data...")
    X, y = generate_synthetic_data(n_samples=10000)

    print(f"📊 Training data shape: {X.shape}")
    print(f"📊 Fraud rate: {y.mean():.2%}")

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    # Train simple RandomForest
    print("🌲 Training RandomForest model...")
    model = RandomForestClassifier(
        n_estimators=50,
        max_depth=10,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    # Evaluate
    train_score = model.score(X_train, y_train)
    test_score = model.score(X_test, y_test)
    print(f"✅ Train accuracy: {train_score:.2%}")
    print(f"✅ Test accuracy: {test_score:.2%}")

    # Save model
    model_dir = Path(__file__).parent.parent / "model"
    model_dir.mkdir(exist_ok=True)

    model_path = model_dir / "fraud_detector.pkl"
    with model_path.open("wb") as f:
        pickle.dump(model, f)

    print(f"💾 Model saved to: {model_path}")
    print("✨ Done!")


if __name__ == "__main__":
    main()
