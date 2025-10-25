# Решение проблем

## Частые проблемы и решения

### Проблемы с установкой

#### `uv sync` не работает

**Проблема:** Зависимости не устанавливаются

**Решения:**
```bash
# Обновите uv
pip install --upgrade uv

# Попробуйте с подробным выводом
uv sync --verbose

# Очистите кэш
rm -rf .venv
uv sync
```

#### Не могу подключиться к API

**Проблема:** `test_api_connection.py` выдаёт ошибки

**Решения:**
1. Проверьте что файл `.env` существует (скопируйте из `.env.example`)
2. Убедитесь что `API_BASE_URL=https://api.de-retreat.mock.events`
3. Проверьте интернет-соединение
4. Спросите у инструктора, запущены ли сервисы

---

## Фаза 1: Проблемы с Crontab

#### Задача cron не запускается

**Проблема:** Скрипт не выполняется по расписанию

**Решения:**
```bash
# Проверьте что cron работает
sudo systemctl status cron

# Посмотрите логи cron
grep CRON /var/log/syslog

# Сначала протестируйте команду вручную
cd /путь/к/phase1_crontab && uv run python fraud_detection.py

# Используйте абсолютные пути в crontab
which uv  # Получите полный путь к uv
pwd       # Получите полный путь к директории
```

#### Permission denied

**Проблема:** `./fraud_detection.py: Permission denied`

**Решение:**
```bash
chmod +x fraud_detection.py
```

#### ModuleNotFoundError

**Проблема:** `No module named 'shared'`

**Решение:**
```bash
# Убедитесь что запускаете из директории phase1_crontab
cd phase1_crontab
uv run python fraud_detection.py

# Crontab требует абсолютные пути
*/2 * * * * cd /полный/путь/к/phase1_crontab && /полный/путь/к/uv run python fraud_detection.py
```

---

## Фаза 2: Проблемы с Dramatiq

#### Redis connection refused

**Проблема:** `Connection refused` при запуске воркеров

**Решение:**
```bash
# Запустите Redis
cd phase2_dramatiq
docker-compose up -d

# Проверьте что Redis запущен
docker-compose ps
docker-compose logs redis

# Протестируйте соединение с Redis
redis-cli ping  # Должен вернуть PONG
```

#### Воркеры не обрабатывают задачи

**Проблема:** Задачи в очереди, но не выполняются

**Решения:**
```bash
# Проверьте что воркеры запущены
ps aux | grep dramatiq

# Запустите воркеров (из директории phase2_dramatiq)
uv run dramatiq tasks --processes 2 --threads 4

# Проверьте Redis на наличие сообщений в очереди
redis-cli
> KEYS *
> LLEN default  # Проверьте длину очереди
```

#### Timeout при `.get_result()`

**Проблема:** Исключение `ResultTimeout`

**Объяснение:** Это ожидаемо! API специально медленный/нестабильный.

**Решения:**
- Увеличьте timeout: `.get_result(timeout=120000)` (2 минуты)
- Падения API мерчантов нормальны - скрипт использует дефолтные значения
- Проверьте логи чтобы увидеть какие конкретно merchant_id тормозят

---

## Фаза 3: Проблемы с Airflow

#### Airflow долго запускается

**Проблема:** `docker-compose up` зависает

**Решение:**
```bash
# Это нормально - подождите 2-3 минуты для инициализации
# Следите за логами чтобы видеть прогресс
docker-compose logs -f airflow-init

# Если застряло больше 5 минут, перезапустите
docker-compose down
docker-compose up -d
```

#### DAG не появляется в UI

**Проблема:** `fraud_detection_pipeline` нет в списке DAG

**Решения:**
```bash
# Проверьте на ошибки импорта
docker-compose exec airflow-webserver airflow dags list

# Посмотрите логи scheduler
docker-compose logs airflow-scheduler

# Частая проблема: синтаксическая ошибка в файле DAG
# Исправьте синтаксис и подождите 1-2 минуты для обновления
```

На новые даги даг-парсер проверяет раз в пять минут, но это можно настроить

#### Ошибки импорта DAG

**Проблема:** Красный баннер в UI Airflow

**Решения:**
1. Проверьте синтаксис Python в `dags/fraud_detection_dag.py`
2. Убедитесь что директории shared/ и model/ примонтированы
3. Проверьте логи: `docker-compose logs airflow-scheduler`

**Частые ошибки:**
```python
# Неправильно - нет return
def my_task(**context):
    result = {"data": 123}
    # а где..

# Правильно
def my_task(**context):
    result = {"data": 123}
    return result
```

#### Ошибки сериализации XCom

**Проблема:** `Object of type 'X' is not JSON serializable`

**Решение:**
Убедитесь что возвращаете JSON-сериализуемые типы:
```python
# Неправильно
return pandas_dataframe  # Нельзя сериализовать

# Правильно
return pandas_dataframe.to_dict(orient='records')
```

Но конечно в XCom лучше не возвращать никаких данных напрямую

#### Задача зависла бесконечно

**Проблема:** Задача застряла в статусе "running"

**Решения:**
```bash
# Проверьте логи задачи в UI (нажмите на задачу → кнопка Log)

# Вероятная причина: таймаут API
# Это ожидаемо - подождите или убейте задачу

# Очистить состояние задачи
docker-compose exec airflow-webserver airflow tasks clear fraud_detection_pipeline -t имя_задачи
```

#### Не могу зайти в UI Airflow

**Проблема:** `http://localhost:8080` не загружается

**Решения:**
```bash
# Проверьте что webserver запущен
docker-compose ps

# Проверьте логи
docker-compose logs airflow-webserver

# Убедитесь что порт не занят
lsof -i :8080

# Перезапустите Airflow
docker-compose restart airflow-webserver
```

---

## Проблемы с API

#### API Merchant Risk всегда выдаёт таймаут

**Проблема:** ВСЕ запросы падают

**Объяснение:** Этот API специально нестабильный!

**Ожидаемое поведение:**
- ~30% таймаутов
- ~10% ошибок 500
- Это НОРМАЛЬНО - используйте дефолтные risk score

**Это не баг если:**
- Некоторые запросы проходят успешно
- Пайплайн продолжает работу с дефолтами
- Метрики показывают рост `api_failures_total{service="merchants"}`

**Это БАГ если:**
- 100% запросов падают
- Проверьте у инструктора - API может быть выключен

#### Слишком много транзакций

**Проблема:** Получаю тысячи транзакций

**Решение:**
- Уменьшите `FETCH_WINDOW_MINUTES` в `.env`
- Используйте `minutes=2` вместо `minutes=15`

---

## Проблемы с метриками/мониторингом

#### Метрики не появляются в Grafana

**Проблема:** Не вижу свои метрики

**Решения:**
1. Проверьте что `PARTICIPANT_NAME` в `.env` установлен
2. Проверьте что URL Pushgateway правильный
3. Убедитесь что metrics.push() вызывается
4. Спросите у инструктора URL дашборда Grafana

#### Pushgateway connection refused

**Проблема:** Не удалось отправить метрики

**Решения:**
```bash
# Проверьте URL
curl https://metrics.de-retreat.mock.events

# Проверьте .env
cat .env | grep PUSHGATEWAY_URL

# Протестируйте вручную
uv run python scripts/test_api_connection.py
```

---

## Проблемы с производительностью

#### Пайплайн выполняется слишком долго

**Проблема:** Время выполнения >5 минут

**Причины:**
1. Таймауты API мерчантов (ожидаемо - небольшая задержка нормальна)
2. Слишком много транзакций (уменьшите окно выборки)
3. Последовательная обработка (ожидаемо в Фазе 1)

**Решения по фазам:**
- **Фаза 1:** Смиритесь - это и есть боль!
- **Фаза 2:** Воркеры обрабатывают параллельно - должно быть быстрее
- **Фаза 3:** Проверьте настройки параллелизма задач в Airflow

---

## Проблемы с Docker

#### Docker закончилось место

**Проблема:** No space left on device

**Решение:**
```bash
# Очистите Docker
docker system prune -a
docker volume prune

# Проверьте место
docker system df
```

#### Порт уже используется

**Проблема:** Порт 6379/8080 уже занят

**Решение:**
```bash
# Найдите что использует порт
sudo lsof -i :6379
sudo lsof -i :8080

# Убейте процесс или измените порт в docker-compose.yml
```

---

## Общие советы по отладке

### Включите подробное логирование

```python
# В вашем скрипте
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Проверьте что на самом деле в XCom

```python
# В задаче Airflow
task_instance = context['task_instance']
data = task_instance.xcom_pull(task_ids='previous_task')
print(f"DEBUG: XCom data = {data}")
```

### Протестируйте отдельные функции

```python
# Тестируйте вне пайплайна
from shared.api_client import fetch_recent_transactions
from shared.config import Config

config = Config.load()
transactions = fetch_recent_transactions(config, minutes=2)
print(f"Получено {len(transactions)} транзакций")
```

### Следите за логами в реальном времени

```bash
# Фаза 1
tail -f phase1_crontab/logs/fraud_detection.log

# Фаза 2
# Логи воркеров идут в stdout
uv run dramatiq tasks --verbose

# Фаза 3
docker-compose logs -f airflow-scheduler
```

---

## ААААААААААААААААААААА

Если всё ещё застряли:

1. **Проверьте логи** - Большинство ошибок содержат полезные сообщения
2. **Спросите соседа** - Возможно они столкнулись с той же проблемой
4. **Проверьте этот док** - Используйте Ctrl+F для поиска

## Известные проблемы воркшопа

Это НАМЕРЕННЫЕ неудобства для обучения:

✅ API мерчантов нестабилен - это ожидаемо!
✅ В Фазе 1 нет retry логики - вы добавите её в Фазе 2!
✅ Отладка cron сложна - в этом и смысл!
✅ Некоторые падения нормальны - обрабатывайте их корректно!

**Если это раздражает, значит башка варит, обучение идёт! 🎓**
