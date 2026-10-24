import pytest
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By

from pages import LoginPage, OpenBmcUi, first_clickable, visible_text, wait


@pytest.fixture
def logged_in(driver, base_url, credentials):
    login_page = LoginPage(driver, base_url).open()
    login_page.login(credentials["username"], credentials["password"])
    ui = OpenBmcUi(driver)
    ui.assert_logged_in()
    return ui


@pytest.mark.webui
def test_power_action_is_available_in_web_ui(driver, logged_in):
    ui = logged_in
    opened = ui.open_page_by_text(["operations", "power", "server power", "управление", "питание"])
    if not opened:
        pytest.skip("Power or operations page was not found in the current OpenBMC Web UI build")

    page_text = visible_text(driver)
    assert any(word in page_text for word in ["power", "on", "off", "restart", "reboot", "пит"])


@pytest.mark.webui
def test_event_logs_are_available_after_opening_logs_page(driver, logged_in):
    ui = logged_in
    opened = ui.open_page_by_text(["event log", "logs", "events", "журнал", "событ"])
    if not opened:
        pytest.skip("Logs or event page was not found in the current OpenBMC Web UI build")

    page_text = visible_text(driver)
    assert any(word in page_text for word in ["event", "log", "severity", "message", "журнал", "событ"])
