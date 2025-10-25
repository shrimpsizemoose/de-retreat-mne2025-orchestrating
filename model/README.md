# Fraud Detection Model

Предобученная простая модель для fraud detection на базе RandomForest.

## Как испоользовать

```python
from shared.model_loader import load_model, predict_fraud
from shared.feature_engineering import engineer_features

model = load_model()

features_df = engineer_features(transactions, user_features, merchant_risks)

predictions = predict_fraud(model, features_df)
```

## Фичи модели

Смотрим в `model_info.json`, там всё есть

## Ещё про модель

Супер-простая модель ещё и обученная на синтетических данных. Будьте добрее к ней, она тупее опоссумов из Ледникового Периода! Смысл воркшопа в оркестрации а не в качестве модели.

- Expected fraud rate: 2-5%
- Accuracy: ~85-90% на тесте

## Как перегенерить модель

Если очень хочется, то можно:

```bash
uv run python scripts/generate_model.py
```
