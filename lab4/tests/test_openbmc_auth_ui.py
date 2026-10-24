import pytest
from selenium.common.exceptions import TimeoutException

from pages import LoginPage, OpenBmcUi


@pytest.mark.auth
def test_successful_login(driver, base_url, credentials):
    login_page = LoginPage(driver, base_url).open()
    login_page.login(credentials["username"], credentials["password"])
    OpenBmcUi(driver).assert_logged_in()


@pytest.mark.auth
def test_invalid_login_shows_error(driver, base_url):
    login_page = LoginPage(driver, base_url).open()
    login_page.login("wrong_user", "wrong_password")
    message = login_page.error_text().lower()
    assert any(word in message for word in ["invalid", "error", "failed", "невер", "ошиб"])


@pytest.mark.auth
def test_repeated_invalid_login_is_handled(driver, base_url):
    login_page = LoginPage(driver, base_url).open()
    messages = []
    for attempt in range(3):
        login_page.login("root", f"bad_password_{attempt}")
        messages.append(login_page.error_text().lower())
    combined = " ".join(messages)
    assert any(word in combined for word in ["invalid", "error", "failed", "locked", "невер", "ошиб", "блок"])
