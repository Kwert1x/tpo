# Лабораторная работа № 5

## Тема

Разработка автотестов для API Redfish с использованием PyTest.

## Реализованные проверки

- создание Redfish-сессии и получение `X-Auth-Token`;
- получение `/redfish/v1/Systems/system` и проверка `Status`, `PowerState`;
- включение системы через `ComputerSystem.Reset` с `ResetType: On`;
- проверка температуры CPU по данным Redfish;
- сравнение показаний CPU в Redfish и IPMI.

Код организован в требуемом файле `test_redfish.py`. Одна сессия повторно используется через `pytest.fixture`, сетевые ошибки диагностируются, а подробный журнал сохраняется в `reports/test_redfish.log`.

## Подготовка окружения

```bash
cd ~/tpo/tpo_lab5/lab5
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Запустите OpenBMC с перенаправлением HTTPS-порта `2443` и IPMI-порта `2623`, затем задайте параметры без сохранения пароля в Git:

```bash
export OPENBMC_BASE_URL="https://127.0.0.1:2443"
export OPENBMC_USERNAME="root"
export OPENBMC_PASSWORD="<пароль OpenBMC>"
export IPMI_HOST="127.0.0.1"
export IPMI_PORT="2623"
```

## Запуск

Без изменения питания системы:

```bash
pytest -v --html=reports/pytest.html --self-contained-html
```

Полный прогон, включая команду включения системы:

```bash
RUN_POWER_TEST=1 pytest -v --html=reports/pytest.html --self-contained-html
```

Тест питания намеренно требует явного `RUN_POWER_TEST=1`. Проверка принимает предписанный заданием `202 Accepted` и совместимый с Redfish ответ `204 No Content`, который возвращает используемый образ OpenBMC. Если QEMU не эмулирует управляемый сервер или датчики, аппаратно-зависимые проверки отмечаются как `SKIPPED` с точной причиной; на физическом стенде выполняются все утверждения.

## Состав

- `test_redfish.py` — пять интеграционных тестов, фикстура Redfish-сессии и вспомогательные функции;
- `pytest.ini` — настройки и маркеры тестов;
- `requirements.txt` — зафиксированные зависимости;
- `reports/` — результаты фактического прогона;
- `Отчёт по лабораторной работе 5.docx` — отчёт для сдачи.
