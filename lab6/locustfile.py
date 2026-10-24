"""Locust scenarios for OpenBMC and public APIs."""

from __future__ import annotations

import os

import urllib3
from locust import HttpUser, between, events, tag, task


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@events.init_command_line_parser.add_listener
def add_arguments(parser):
    parser.add_argument(
        "--openbmc-url",
        env_var="OPENBMC_BASE_URL",
        default="https://127.0.0.1:2443",
        help="OpenBMC base URL",
    )
    parser.add_argument(
        "--openbmc-username",
        env_var="OPENBMC_USERNAME",
        default=None,
        help="OpenBMC user name",
    )
    parser.add_argument(
        "--openbmc-password",
        env_var="OPENBMC_PASSWORD",
        default=None,
        help="OpenBMC password",
        is_secret=True,
    )


class OpenBMCUser(HttpUser):
    """Load profile for the OpenBMC Redfish API."""

    host = os.getenv("OPENBMC_BASE_URL", "https://127.0.0.1:2443")
    wait_time = between(1, 3)
    weight = 1

    def on_start(self):
        options = self.environment.parsed_options
        self.host = options.openbmc_url.rstrip("/")
        username = options.openbmc_username
        password = options.openbmc_password
        if not username or not password:
            raise RuntimeError(
                "OPENBMC_USERNAME and OPENBMC_PASSWORD are required for OpenBMC load tests"
            )

        with self.client.post(
            "/redfish/v1/SessionService/Sessions",
            json={"UserName": username, "Password": password},
            verify=False,
            name="POST Redfish session",
            catch_response=True,
        ) as response:
            if response.status_code not in (200, 201):
                response.failure(f"authentication returned HTTP {response.status_code}")
                raise RuntimeError("OpenBMC authentication failed")
            token = response.headers.get("X-Auth-Token")
            if not token:
                response.failure("authentication response has no X-Auth-Token")
                raise RuntimeError("OpenBMC authentication returned no token")
            self.client.headers.update({"X-Auth-Token": token, "Accept": "application/json"})
            self.session_location = response.headers.get("Location")

    def on_stop(self):
        if getattr(self, "session_location", None):
            self.client.delete(self.session_location, verify=False, name="DELETE Redfish session")

    @tag("openbmc")
    @task(2)
    def system_information(self):
        with self.client.get(
            "/redfish/v1/Systems/system",
            verify=False,
            name="GET Redfish system",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"expected HTTP 200, got {response.status_code}")
                return
            try:
                payload = response.json()
            except ValueError:
                response.failure("response is not JSON")
                return
            if "Status" not in payload:
                response.failure("response has no Status")

    @tag("openbmc")
    @task(1)
    def power_state(self):
        with self.client.get(
            "/redfish/v1/Systems/system",
            verify=False,
            name="GET Redfish PowerState",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"expected HTTP 200, got {response.status_code}")
                return
            try:
                power_state = response.json().get("PowerState")
            except ValueError:
                response.failure("response is not JSON")
                return
            if power_state not in {"On", "Off", "PoweringOn", "PoweringOff"}:
                response.failure(f"unexpected PowerState: {power_state!r}")


class PublicApiUser(HttpUser):
    """Load profile for JSONPlaceholder and wttr.in."""

    host = "https://jsonplaceholder.typicode.com"
    wait_time = between(1, 3)
    weight = 1

    @tag("public")
    @task(2)
    def posts(self):
        with self.client.get("/posts", name="GET JSONPlaceholder /posts", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"expected HTTP 200, got {response.status_code}")
                return
            try:
                payload = response.json()
            except ValueError:
                response.failure("response is not JSON")
                return
            if not isinstance(payload, list) or not payload:
                response.failure("posts response is empty")

    @tag("public")
    @task(1)
    def weather(self):
        with self.client.get(
            "https://wttr.in/Novosibirsk?format=j1",
            name="GET wttr.in Novosibirsk",
            headers={"User-Agent": "tpo-lab6-locust/1.0"},
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"expected HTTP 200, got {response.status_code}")
                return
            try:
                payload = response.json()
            except ValueError:
                response.failure("response is not JSON")
                return
            if "current_condition" not in payload:
                response.failure("weather response has no current_condition")
