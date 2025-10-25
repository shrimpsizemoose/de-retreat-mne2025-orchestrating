# Фаза 3: Airflow

Реализуйте тот же пайплайн как Airflow DAG. Что нам это даст:
- Визуализацию DAG в веб-интерфейсе
- Автоматические retry и управление зависимостями
- XCom для передачи данных между задачами
- UI для мониторинга и отладки

## Ваша задача

1. Завершите реализацию DAG в `dags/fraud_detection_dag.py`
2. Определите операторы для каждого шага пайплайна
3. Настройте зависимости между задачами
4. Используйте XCom для передачи данных

## Установка и запуск

### 1. Установите Airflow

Лучше делать это в отдельном виртуальном окружении

```bash
# Установите Airflow через pip (nb флаг constraint)
pip install "apache-airflow==3.1.0" --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-3.1.0/constraints-3.10.txt"
```

⚠️ **Важно:** Airflow рекомендуется устанавливать через pip, а не uv, из-за сложных зависимостей.

### 2. Запустите PostgreSQL

```bash
cd phase3_airflow

# Запустите только PostgreSQL для Airflow
docker-compose up -d

# Проверьте что база запустилась
docker-compose logs postgres
```

### 3. Запустите Airflow

```bash
# Установите AIRFLOW_HOME в текущую директорию
export AIRFLOW_HOME=$(pwd)

# Запустите Airflow (инициализация БД + веб-сервер + scheduler)
airflow standalone
```

⚠️ **Важно:** Первый запуск может занять 1-2 минуты для инициализации базы данных.

### 4. Получите доступ к веб-интерфейсу

Откройте в браузере: **http://localhost:8080**

Логин и пароль будут выведены в консоли при первом запуске `airflow standalone`.

### 5. Активируйте DAG

1. Найдите `fraud_detection_pipeline` в списке DAGs
2. Включите его переключателем слева
3. Запустите вручную кнопкой ▶️ (для тестирования)

## Структура директории

```
phase3_airflow/
├── dags/
│   └── fraud_detection_dag.py   # Ваш DAG (с TODO)
├── logs/                         # Логи Airflow
├── results/                      # Результаты пайплайна
└── docker-compose.yml           # Airflow stack
```

⚠️ **Важно:** Airflow scheduler сканирует директорию `dags/` каждые 60 секунд. Изменения в DAG подхватываются автоматически, но может потребоваться 1-2 минуты.

## Ключевые концепции Airflow

### DAG (Directed Acyclic Graph)

```python
from airflow import DAG

dag = DAG(
    'my_pipeline',
    schedule_interval='*/2 * * * *',  # Каждые 2 минуты
    catchup=False,  # Не запускать пропущенные периоды
)
```

### Operators

```python
from airflow.operators.python import PythonOperator

task = PythonOperator(
    task_id='my_task',
    python_callable=my_function,
    dag=dag,
)
```

### XCom (Cross-Communication)

Передача данных между задачами:

```python
def task1(**context):
    result = {"data": "value"}
    # Push to XCom
    context['task_instance'].xcom_push(key='my_key', value=result)
    # Or just return (auto-pushes with key 'return_value')
    return result

def task2(**context):
    # Pull from XCom
    data = context['task_instance'].xcom_pull(
        task_ids='task1',
        key='return_value'
    )
```

### Task Dependencies

```python
# Linear chain
task1 >> task2 >> task3

# параллельные ветки
task1 >> [task2, task3] >> task4
```

## Тестирование

### Запустить DAG вручную

В веб-интерфейсе: кнопка ▶️ справа от DAG

### Посмотреть Graph View

DAG → Graph - визуализация зависимостей и статусов

### Посмотреть логи задачи

Кликните на задачу → Log

### Посмотреть XCom данные

Кликните на задачу → XCom

### Протестировать задачу локально

```bash
# В отдельном терминале (с установленным AIRFLOW_HOME)
export AIRFLOW_HOME=$(pwd)
airflow tasks test fraud_detection_pipeline fetch_transactions 2025-01-25
```

## Преимущества vs Dramatiq

✅ **Визуализация DAG** - видите граф зависимостей
✅ **Богатый UI** - логи, метрики, XCom - всё в одном месте
✅ **Backfilling** - легко перезапустить прошлые периоды
✅ **SLA monitoring** - алерты при превышении времени
✅ **Много готовых операторов** - для баз данных, облаков, etc.

## Недостатки vs Dramatiq

❌ **Тяжелая инфраструктура** - Docker, база данных, веб-сервер
❌ **Более сложная настройка** - больше конфигурации
❌ **Overhead для простых задач** - избыточен для маленьких пайплайнов

## Отладка

### DAG не появляется

```bash
# Проверьте ошибки парсинга
export AIRFLOW_HOME=$(pwd)
airflow dags list

# Проверьте синтаксис DAG файла
python -m py_compile dags/fraud_detection_dag.py

# Посмотрите логи в терминале где запущен airflow standalone
```

### Задача зависла

- Проверьте логи задачи в UI
- Проверьте timeout settings
- Merchant API может быть медленным - это ожидаемо!

### Остановить и очистить

```bash
# Остановить Airflow (Ctrl+C в терминале где запущен airflow standalone)

# Остановить PostgreSQL
docker-compose down

# Удалить данные PostgreSQL (сбросить всё)
docker-compose down -v

# Очистить метаданные Airflow (опционально)
rm -rf airflow.db airflow-webserver.pid logs/
```

## Время выполнения

50-60 минут на реализацию
