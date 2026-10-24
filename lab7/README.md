# Лабораторная работа № 7

## Тема

CI/CD для тестирования OpenBMC с GitHub, Jenkins и Docker.

## Реализованный Pipeline

`Jenkinsfile` выполняет требуемые этапы:

1. получает ветки `lab5`, `lab4`, `lab6` из GitHub;
2. запускает образ OpenBMC в QEMU и ждёт готовности Redfish;
3. запускает API-тесты PyTest из `lab5`;
4. запускает WebUI-тесты Selenium из `lab4`;
5. запускает нагрузочное тестирование Locust из `lab6`;
6. сохраняет отчёты каждого этапа в артефакты Jenkins;
7. останавливает QEMU независимо от результата сборки.

## Развёртывание Jenkins в Docker

Создайте локальный файл `.env` по примеру:

```bash
cd ~/tpo/tpo_lab7/lab7
cp .env.example .env
```

Убедитесь, что `OPENBMC_IMAGE_PATH` содержит абсолютный путь к образу, затем выполните:

```bash
docker compose up -d --build
docker compose ps
docker exec tpo-jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

Jenkins будет доступен по адресу `http://localhost:8080`.

## Настройка Jenkins

1. Завершите мастер первоначальной настройки и установите рекомендуемые плагины.
2. В **Manage Jenkins → Credentials → System → Global credentials** создайте запись типа **Username with password**:
   - ID: `openbmc-credentials`;
   - Username: пользователь OpenBMC;
   - Password: пароль OpenBMC.
3. Создайте **Pipeline** и выберите **Pipeline script from SCM**.
4. Укажите репозиторий `https://github.com/Kwert1x/tpo.git`, ветку `*/lab7` и путь `lab7/Jenkinsfile`.
5. Запустите сборку после публикации веток `lab5`, `lab6`, `lab7`.

## Артефакты

- `artifacts/qemu/` — консоль QEMU и ответ корневого Redfish API;
- `artifacts/api/` — JUnit XML, HTML и консоль API-тестов;
- `artifacts/webui/` — JUnit XML, HTML, консоль и диагностические скриншоты Selenium;
- `artifacts/load/` — CSV, HTML и консоль Locust.

Пароли не записываются в репозиторий и передаются Pipeline через Jenkins Credentials.
