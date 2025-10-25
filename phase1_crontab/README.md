# Фаза 1: Crontab

Пайплайн детекции мошенничества как простой Python-скрипт, запускаемый по расписанию cron.

Наипростейший подход - просто скрипт на питоне, щедулится кроном. Ощутите боль обработки ошибок, отсутсвтия проверок ну и того что это сложно параллелить.


## Задача

1. Завершить реализацию `fraud_detection.py`, заполнив все TODO секции
2. Сфокусируйтесь на:
   - Обработке ошибок (API будут падать!)
   - Логировании (оно вам понадобится для отладки)
   - Отправке метрик (пуш в Pushgateway инструктора)

## Установка

```bash
# Сделайте скрипт исполняемым
chmod +x fraud_detection.py

# Тестовый запуск вручную
./fraud_detection.py

# Или через uv
uv run python fraud_detection.py
```

## Настройка Crontab

```bash
# Откройте редактор crontab
crontab -e

# Добавьте строку для запуска каждые 2 минуты
*/2 * * * * cd /home/user/path-to-repo/phase1_crontab && /home/user/.local/bin/uv run python fraud_detection.py >> logs/cron.log 2>&1
```

⚠️ **Важно:** Замените путь на актуальный!

## Тестирование

```bash
# Запустите вручную
uv run python fraud_detection.py

# Проверьте логи
tail -f logs/fraud_detection.log

# Проверьте, что метрики были отправлены (в Grafana)
```

## Порефлексируйте про боли, которые вы испытаете

- ❌ Что происходит, когда API merchant-risk падает с таймаутом?
- ❌ Что происходит, если скрипт выполняется дольше 2 минут?
- ❌ Как отлаживать падения?
- ❌ Как узнать, что cron вообще запускается?
- ❌ Что делать с зависимостями между шагами?

## Några tips

### Обработка нестабильного API

API `merchant-risk` умышленно нестабилен. Поможет try/except, чтобы возвращать дефолтные значения, типа:

```python
try:
    risk = fetch_merchant_risk(config, merchant_id)
except APIError:
    metrics.record_api_failure("merchants")
    risk = DEFAULT_MERCHANT_RISK
```

### Логирование

Логируйте всё важное:

```python
logger.info(f"Fetched {len(transactions)} transactions")
logger.warning(f"Merchant API failed for {merchant_id}")
logger.error(f"Pipeline failed: {e}", exc_info=True)
```

### Метрики

Не забудьте отправить метрики даже при ошибках:

```python
try:
    # ... pipeline logic ...
    metrics.record_fraud_rate(fraud_rate)
    metrics.push()
except Exception as e:
    # Даже если пайплайн упал, попытайтесь отправить что-то
    metrics.record_duration(time.time() - start_time)
    metrics.push()
    raise
```

## Время выполнения

30-40 минут на реализацию
