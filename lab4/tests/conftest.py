import os
import socket
from pathlib import Path
from urllib.parse import urlparse

import pytest
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"


def pytest_addoption(parser):
    parser.addoption(
        "--base-url",
        action="store",
        default=os.getenv("OPENBMC_BASE_URL", "https://127.0.0.1:2443"),
        help="OpenBMC Web UI base URL",
    )
    parser.addoption(
        "--browser",
        action="store",
        default=os.getenv("SELENIUM_BROWSER", "chrome"),
        choices=("chrome", "edge", "firefox"),
        help="Browser for Selenium WebDriver",
    )


def _is_tcp_port_open(url):
    parsed = urlparse(url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((host, port), timeout=3):
            return True
    except OSError:
        return False


@pytest.fixture(scope="session")
def base_url(pytestconfig):
    url = pytestconfig.getoption("--base-url").rstrip("/")
    if not _is_tcp_port_open(url):
        pytest.skip(f"OpenBMC Web UI is not reachable at {url}")
    return url


@pytest.fixture(scope="session")
def credentials():
    username = os.getenv("OPENBMC_USERNAME")
    password = os.getenv("OPENBMC_PASSWORD")
    if not username or not password:
        pytest.skip(
            "Set OPENBMC_USERNAME and OPENBMC_PASSWORD to run authentication tests"
        )
    return {
        "username": username,
        "password": password,
    }


@pytest.fixture
def driver(pytestconfig, request):
    ARTIFACTS_DIR.mkdir(exist_ok=True)
    browser = pytestconfig.getoption("--browser")
    headless = os.getenv("SELENIUM_HEADLESS", "1") != "0"

    try:
        if browser == "chrome":
            options = ChromeOptions()
            options.page_load_strategy = "eager"
            if headless:
                options.add_argument("--headless=new")
            options.add_argument("--ignore-certificate-errors")
            options.add_argument("--allow-insecure-localhost")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1440,1000")
            drv = webdriver.Chrome(options=options)
        elif browser == "edge":
            options = EdgeOptions()
            options.page_load_strategy = "eager"
            if headless:
                options.add_argument("--headless=new")
            options.add_argument("--ignore-certificate-errors")
            options.add_argument("--allow-insecure-localhost")
            options.add_argument("--window-size=1440,1000")
            drv = webdriver.Edge(options=options)
        else:
            options = FirefoxOptions()
            options.page_load_strategy = "eager"
            if headless:
                options.add_argument("-headless")
            options.accept_insecure_certs = True
            drv = webdriver.Firefox(options=options)
    except WebDriverException as exc:
        pytest.skip(f"Selenium WebDriver could not start {browser}: {exc.msg}")

    drv.set_page_load_timeout(30)
    yield drv

    if hasattr(request.node, "rep_call") and request.node.rep_call.failed:
        safe_name = request.node.nodeid.replace("/", "_").replace("::", "__")
        drv.save_screenshot(str(ARTIFACTS_DIR / f"{safe_name}.png"))
    drv.quit()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)
