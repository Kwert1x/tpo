# Лабораторная работа № 4

## Тема

Разработка автотестов OpenBMC Web UI с использованием Selenium.

## Структура

- `tests/` — тесты авторизации и функций Web UI, фикстуры и Page Object;
- `reports/pytest_openbmc_run.txt` — сохранённый результат запуска pytest;
- `pytest.ini` — конфигурация и маркеры pytest;
- `requirements.txt` — зависимости проекта;
- `Тестирование лаб4.docx` — редактируемая версия отчёта;
- `Тестирование лаб4.pdf` — версия отчёта для просмотра и сдачи.

## Подготовка окружения

```bash
cd ~/tpo/tpo/lab4
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Для Selenium должен быть установлен Chrome, Chromium, Edge или Firefox с подходящим WebDriver.

## Запуск OpenBMC

В отдельном окне WSL из каталога с образом OpenBMC:

```bash
qemu-system-arm -m 256 -M romulus-bmc -nographic \
  -drive file=obmc-phosphor-image-romulus.static.mtd,format=raw,if=mtd \
  -net nic \
  -net user,hostfwd=:0.0.0.0:2222-:22,hostfwd=:0.0.0.0:2443-:443,hostfwd=udp:0.0.0.0:2623-:623,hostname=qemu
```

После загрузки Web UI должен быть доступен по адресу `https://127.0.0.1:2443`.

## Запуск тестов

В каталоге `lab4`:

```bash
source .venv/bin/activate

export OPENBMC_BASE_URL="https://127.0.0.1:2443"
export OPENBMC_USERNAME="root"
export OPENBMC_PASSWORD="<пароль OpenBMC>"
export SELENIUM_BROWSER="chrome"
export SELENIUM_HEADLESS="1"

pytest -v
```

Если нужная страница отсутствует в текущей сборке OpenBMC, соответствующий Web UI тест будет корректно пропущен с указанием причины. Скриншоты ошибок сохраняются локально в `artifacts/` и не добавляются в Git.
