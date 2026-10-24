import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse, urlunparse
from urllib.request import Request, urlopen

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


DEFAULT_TIMEOUT = 8


def wait(driver, timeout=DEFAULT_TIMEOUT):
    return WebDriverWait(driver, timeout)


def first_present(driver, locators, timeout=DEFAULT_TIMEOUT):
    last_error = None
    for locator in locators:
        try:
            return wait(driver, timeout).until(EC.presence_of_element_located(locator))
        except TimeoutException as exc:
            last_error = exc
    raise last_error


def first_clickable(driver, locators, timeout=DEFAULT_TIMEOUT):
    last_error = None
    for locator in locators:
        try:
            return wait(driver, timeout).until(EC.element_to_be_clickable(locator))
        except TimeoutException as exc:
            last_error = exc
    raise last_error


def visible_text(driver):
    return driver.find_element(By.TAG_NAME, "body").text.lower()


class LoginPage:
    USERNAME = [
        (By.CSS_SELECTOR, "input[name='username']"),
        (By.CSS_SELECTOR, "input#username"),
        (By.CSS_SELECTOR, "input[autocomplete='username']"),
        (By.CSS_SELECTOR, "input[type='text']"),
    ]
    PASSWORD = [
        (By.CSS_SELECTOR, "input[name='password']"),
        (By.CSS_SELECTOR, "input#password"),
        (By.CSS_SELECTOR, "input[autocomplete='current-password']"),
        (By.CSS_SELECTOR, "input[type='password']"),
    ]
    SUBMIT = [
        (By.CSS_SELECTOR, "button[type='submit']"),
        (By.XPATH, "//button[contains(translate(., 'LOGINВОЙТИ', 'loginвойти'), 'login')]"),
        (By.XPATH, "//button[contains(translate(., 'LOGINВОЙТИ', 'loginвойти'), 'войти')]"),
    ]
    ERROR = [
        (By.CSS_SELECTOR, "[role='alert']"),
        (By.CSS_SELECTOR, ".alert-danger"),
        (By.CSS_SELECTOR, ".error"),
        (By.CSS_SELECTOR, "[class*='error']"),
        (By.XPATH, "//*[contains(translate(., 'INVALIDERRORНЕВЕРНБЛОК', 'invaliderrorневернблок'), 'invalid') or contains(translate(., 'INVALIDERRORНЕВЕРНБЛОК', 'invaliderrorневернблок'), 'error') or contains(translate(., 'INVALIDERRORНЕВЕРНБЛОК', 'invaliderrorневернблок'), 'неверн') or contains(translate(., 'INVALIDERRORНЕВЕРНБЛОК', 'invaliderrorневернблок'), 'блок')]"),
    ]

    def __init__(self, driver, base_url):
        self.driver = driver
        self.base_url = base_url
        self.uses_form = False
        self.last_error = ""

    def open(self):
        if _server_uses_basic_auth(self.base_url):
            self.uses_form = False
            return self
        self.driver.get(self.base_url)
        try:
            first_present(self.driver, self.USERNAME, timeout=5)
            self.uses_form = True
        except TimeoutException:
            self.uses_form = False
        return self

    def login(self, username, password):
        if self.uses_form:
            username_input = first_present(self.driver, self.USERNAME)
            password_input = first_present(self.driver, self.PASSWORD)
            username_input.clear()
            username_input.send_keys(username)
            password_input.clear()
            password_input.send_keys(password)
            first_clickable(self.driver, self.SUBMIT).click()
        else:
            try:
                self.driver.get(_basic_auth_url(self.base_url, username, password))
            except TimeoutException:
                # Chrome can time out when the server rejects Basic Auth credentials.
                self.last_error = "Basic Auth failed or authorization prompt was shown"

    def error_text(self):
        if self.last_error:
            return self.last_error
        try:
            return first_present(self.driver, self.ERROR, timeout=8).text
        except TimeoutException:
            return visible_text(self.driver)


class OpenBmcUi:
    LOGOUT = [
        (By.CSS_SELECTOR, "button[aria-label*='Log out']"),
        (By.CSS_SELECTOR, "a[href*='logout']"),
        (By.XPATH, "//*[contains(translate(., 'LOG OUTВЫЙТИ', 'log outвыйти'), 'log out') or contains(translate(., 'LOG OUTВЫЙТИ', 'log outвыйти'), 'выйти')]"),
    ]

    def __init__(self, driver):
        self.driver = driver

    def assert_logged_in(self):
        wait(self.driver).until(lambda d: "401" not in d.title.lower())
        body = visible_text(self.driver)
        assert not any(word in body for word in ["unauthorized", "authorization required"])

    def open_page_by_text(self, labels):
        for label in labels:
            candidates = [
                (By.XPATH, f"//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{label.lower()}')]"),
                (By.XPATH, f"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{label.lower()}')]"),
            ]
            try:
                first_clickable(self.driver, candidates, timeout=4).click()
                return True
            except TimeoutException:
                continue
        return False


def _has_any(driver, locators):
    for by, selector in locators:
        if driver.find_elements(by, selector):
            return True
    return False


def _basic_auth_url(url, username, password):
    parsed = urlparse(url)
    netloc = f"{quote(username)}:{quote(password)}@{parsed.hostname}"
    if parsed.port:
        netloc += f":{parsed.port}"
    return urlunparse((parsed.scheme, netloc, parsed.path or "/", parsed.params, parsed.query, parsed.fragment))


def _server_uses_basic_auth(url):
    request = Request(url, method="HEAD")
    context = ssl._create_unverified_context()
    try:
        with urlopen(request, timeout=5, context=context) as response:
            header = response.headers.get("www-authenticate", "")
            return "basic" in header.lower()
    except HTTPError as exc:
        header = exc.headers.get("www-authenticate", "")
        return exc.code == 401 and "basic" in header.lower()
    except (URLError, TimeoutError, OSError):
        return False
