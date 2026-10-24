# Лабораторная работа № 6

## Тема

Разработка сценария нагрузочного тестирования с использованием Locust.

## Сценарии

В `locustfile.py` определены два независимых класса нагрузки:

- `OpenBMCUser` — создание Redfish-сессии, запрос сведений о системе и проверка `PowerState`;
- `PublicApiUser` — получение списка `/posts` у JSONPlaceholder и погоды Новосибирска у `wttr.in`.

Все ответы проверяются по HTTP-коду и структуре JSON. Для OpenBMC TLS-сертификат локального стенда допускается самоподписанный, а пароль передаётся только через окружение.

## Установка

```bash
cd ~/tpo/tpo_lab6/lab6
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Веб-интерфейс Locust

```bash
locust -f locustfile.py
```

Откройте `http://localhost:8089`, укажите 10 пользователей и скорость запуска 2 пользователя/с.

## Автоматический прогон

Публичные API:

```bash
./run_load_tests.sh public
```

OpenBMC:

```bash
export OPENBMC_BASE_URL="https://127.0.0.1:2443"
export OPENBMC_USERNAME="root"
export OPENBMC_PASSWORD="<пароль OpenBMC>"
./run_load_tests.sh openbmc
```

По умолчанию выполняется 30-секундный прогон с 10 пользователями и скоростью запуска 2 пользователя/с. Параметры меняются через `LOCUST_USERS`, `LOCUST_SPAWN_RATE`, `LOCUST_RUN_TIME`.

## Результаты

В `reports/` сохраняются CSV-метрики и автономный HTML-отчёт Locust. В отчёте лабораторной работы приведены средние задержки, процент ошибок и график на основе фактического прогона.
