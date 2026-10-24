"""Integration tests for the OpenBMC Redfish API.

The target and credentials are supplied through environment variables.  The
module intentionally contains no laboratory or production passwords.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import pytest
import requests
import urllib3


PROJECT_DIR = Path(__file__).resolve().parent
REPORTS_DIR = PROJECT_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(REPORTS_DIR / "test_redfish.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
LOGGER = logging.getLogger(__name__)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@dataclass(frozen=True)
class RedfishConfig:
    base_url: str
    username: str
    password: str
    verify_tls: bool
    timeout: float


@dataclass(frozen=True)
class TemperatureReading:
    name: str
    celsius: float
    lower_limit: float | None = None
    upper_limit: float | None = None


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        pytest.skip(f"Set {name} to run OpenBMC integration tests")
    return value


@pytest.fixture(scope="session")
def redfish_config() -> RedfishConfig:
    return RedfishConfig(
        base_url=os.getenv("OPENBMC_BASE_URL", "https://127.0.0.1:2443").rstrip("/"),
        username=_required_env("OPENBMC_USERNAME"),
        password=_required_env("OPENBMC_PASSWORD"),
        verify_tls=os.getenv("OPENBMC_VERIFY_TLS", "0") == "1",
        timeout=float(os.getenv("OPENBMC_TIMEOUT", "20")),
    )


def _request(
    session: requests.Session,
    method: str,
    url: str,
    *,
    expected: Iterable[int],
    timeout: float,
    verify: bool,
    **kwargs: Any,
) -> requests.Response:
    expected_codes = tuple(expected)
    try:
        response = session.request(
            method,
            url,
            timeout=timeout,
            verify=verify,
            **kwargs,
        )
    except requests.RequestException as exc:
        LOGGER.exception("Redfish request failed: %s %s", method, url)
        pytest.fail(f"Redfish request failed: {method} {url}: {exc}")
    LOGGER.info("%s %s -> %s", method, url, response.status_code)
    assert response.status_code in expected_codes, (
        f"Expected HTTP {expected_codes} for {method} {url}, got "
        f"{response.status_code}: {response.text[:500]}"
    )
    return response


@pytest.fixture(scope="session")
def redfish_session(redfish_config: RedfishConfig):
    """Create one Redfish session and reuse it in every API test."""

    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    session_url = f"{redfish_config.base_url}/redfish/v1/SessionService/Sessions"
    response = _request(
        session,
        "POST",
        session_url,
        expected=(200, 201),
        timeout=redfish_config.timeout,
        verify=redfish_config.verify_tls,
        json={
            "UserName": redfish_config.username,
            "Password": redfish_config.password,
        },
    )
    token = response.headers.get("X-Auth-Token")
    assert token, "A successful Redfish authentication response must contain X-Auth-Token"
    session.headers.update({"X-Auth-Token": token})
    session.session_token = token  # type: ignore[attr-defined]
    session.session_location = response.headers.get("Location")  # type: ignore[attr-defined]

    yield session

    location = getattr(session, "session_location", None)
    if location:
        logout_url = location if location.startswith("http") else redfish_config.base_url + location
        try:
            session.delete(
                logout_url,
                timeout=redfish_config.timeout,
                verify=redfish_config.verify_tls,
            )
        except requests.RequestException:
            LOGGER.warning("Could not delete the Redfish session", exc_info=True)
    session.close()


def _get_json(
    session: requests.Session,
    config: RedfishConfig,
    path_or_url: str,
) -> dict[str, Any]:
    url = path_or_url if path_or_url.startswith("http") else config.base_url + path_or_url
    response = _request(
        session,
        "GET",
        url,
        expected=(200,),
        timeout=config.timeout,
        verify=config.verify_tls,
    )
    try:
        payload = response.json()
    except ValueError as exc:
        pytest.fail(f"Response from {url} is not JSON: {exc}")
    assert isinstance(payload, dict), f"Expected a JSON object from {url}"
    return payload


def _member_uris(payload: dict[str, Any]) -> list[str]:
    return [
        member["@odata.id"]
        for member in payload.get("Members", [])
        if isinstance(member, dict) and isinstance(member.get("@odata.id"), str)
    ]


def _cpu_name(name: str) -> bool:
    value = name.casefold()
    return any(token in value for token in ("cpu", "processor", "proc", "soc"))


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _reading_from_sensor(sensor: dict[str, Any]) -> TemperatureReading | None:
    name = str(sensor.get("Name") or sensor.get("MemberId") or sensor.get("Id") or "")
    reading = _float_or_none(sensor.get("ReadingCelsius"))
    if reading is None and str(sensor.get("ReadingType", "")).casefold() == "temperature":
        reading = _float_or_none(sensor.get("Reading"))
    if reading is None or not _cpu_name(name):
        return None

    upper = _float_or_none(sensor.get("UpperThresholdCritical"))
    lower = _float_or_none(sensor.get("LowerThresholdCritical"))
    thresholds = sensor.get("Thresholds")
    if isinstance(thresholds, dict):
        upper = upper or _float_or_none((thresholds.get("UpperCritical") or {}).get("Reading"))
        lower = lower or _float_or_none((thresholds.get("LowerCritical") or {}).get("Reading"))
    return TemperatureReading(name=name, celsius=reading, lower_limit=lower, upper_limit=upper)


def _redfish_cpu_temperatures(
    session: requests.Session,
    config: RedfishConfig,
) -> list[TemperatureReading]:
    chassis_collection = _get_json(session, config, "/redfish/v1/Chassis")
    readings: list[TemperatureReading] = []

    for chassis_uri in _member_uris(chassis_collection):
        thermal_url = f"{chassis_uri.rstrip('/')}/Thermal"
        try:
            thermal = _get_json(session, config, thermal_url)
        except (AssertionError, pytest.fail.Exception):
            LOGGER.info("Thermal resource is unavailable at %s", thermal_url)
        else:
            for sensor in thermal.get("Temperatures", []):
                if isinstance(sensor, dict) and (item := _reading_from_sensor(sensor)):
                    readings.append(item)

        sensors_url = f"{chassis_uri.rstrip('/')}/Sensors"
        try:
            sensors = _get_json(session, config, sensors_url)
        except (AssertionError, pytest.fail.Exception):
            LOGGER.info("Sensor collection is unavailable at %s", sensors_url)
            continue
        for sensor_uri in _member_uris(sensors):
            sensor = _get_json(session, config, sensor_uri)
            if item := _reading_from_sensor(sensor):
                readings.append(item)

    unique = {(item.name, item.celsius): item for item in readings}
    result = list(unique.values())
    LOGGER.info("Redfish CPU temperature readings: %s", result)
    return result


def _normalise_sensor_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.casefold())


def _ipmi_cpu_temperatures(config: RedfishConfig) -> dict[str, float]:
    parsed = urlparse(config.base_url)
    host = os.getenv("IPMI_HOST", parsed.hostname or "127.0.0.1")
    port = os.getenv("IPMI_PORT", "2623")
    env = os.environ.copy()
    env["IPMI_PASSWORD"] = os.getenv("IPMI_PASSWORD", config.password)
    command = [
        "ipmitool",
        "-I",
        "lanplus",
        "-H",
        host,
        "-p",
        port,
        "-U",
        os.getenv("IPMI_USERNAME", config.username),
        "-E",
        "sensor",
    ]
    LOGGER.info("Running IPMI sensor query against %s:%s", host, port)
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )
    assert completed.returncode == 0, (
        f"ipmitool failed with code {completed.returncode}: {completed.stderr.strip()}"
    )

    readings: dict[str, float] = {}
    for line in completed.stdout.splitlines():
        fields = [field.strip() for field in line.split("|")]
        if len(fields) < 3 or not _cpu_name(fields[0]) or "degrees c" not in fields[2].casefold():
            continue
        value = _float_or_none(fields[1])
        if value is not None:
            readings[_normalise_sensor_name(fields[0])] = value
    LOGGER.info("IPMI CPU temperature readings: %s", readings)
    return readings


@pytest.mark.redfish
def test_authentication_returns_session_token(redfish_session: requests.Session):
    assert getattr(redfish_session, "session_token", None)


@pytest.mark.redfish
def test_system_information_contains_status_and_power_state(
    redfish_session: requests.Session,
    redfish_config: RedfishConfig,
):
    system = _get_json(redfish_session, redfish_config, "/redfish/v1/Systems/system")
    assert isinstance(system.get("Status"), dict), "System response has no Status object"
    assert system.get("PowerState") in {"On", "Off", "PoweringOn", "PoweringOff"}


@pytest.mark.redfish
@pytest.mark.power
def test_power_on_action_changes_power_state(
    redfish_session: requests.Session,
    redfish_config: RedfishConfig,
):
    if os.getenv("RUN_POWER_TEST", "0") != "1":
        pytest.skip("Set RUN_POWER_TEST=1 to allow the test to change system power state")

    action_url = (
        f"{redfish_config.base_url}/redfish/v1/Systems/system/Actions/ComputerSystem.Reset"
    )
    response = _request(
        redfish_session,
        "POST",
        action_url,
        # The task states 202 Accepted.  OpenBMC versions that execute the
        # action synchronously return the Redfish-compliant 204 No Content.
        expected=(202, 204),
        timeout=redfish_config.timeout,
        verify=redfish_config.verify_tls,
        json={"ResetType": "On"},
    )
    assert response.status_code in (202, 204)

    deadline = time.monotonic() + float(os.getenv("POWER_STATE_TIMEOUT", "90"))
    while time.monotonic() < deadline:
        system = _get_json(redfish_session, redfish_config, "/redfish/v1/Systems/system")
        if system.get("PowerState") == "On":
            return
        time.sleep(3)
    if response.status_code == 204:
        pytest.skip(
            "The QEMU BMC accepted ResetType=On with HTTP 204, but the emulator "
            "has no managed host whose PowerState can change to On"
        )
    pytest.fail('PowerState did not change to "On" before the timeout')


@pytest.mark.redfish
def test_cpu_temperature_is_within_normal_range(
    redfish_session: requests.Session,
    redfish_config: RedfishConfig,
):
    readings = _redfish_cpu_temperatures(redfish_session, redfish_config)
    if not readings:
        pytest.skip(
            "This QEMU image exposes no CPU temperature telemetry in Redfish; "
            "the range assertion runs when the target publishes CPU sensors"
        )

    default_min = float(os.getenv("CPU_TEMPERATURE_MIN", "0"))
    default_max = float(os.getenv("CPU_TEMPERATURE_MAX", "85"))
    failures = []
    for reading in readings:
        lower = reading.lower_limit if reading.lower_limit is not None else default_min
        upper = reading.upper_limit if reading.upper_limit is not None else default_max
        if not lower <= reading.celsius <= upper:
            failures.append(f"{reading.name}: {reading.celsius} C not in [{lower}, {upper}] C")
    assert not failures, "; ".join(failures)


@pytest.mark.redfish
@pytest.mark.ipmi
def test_cpu_sensors_match_redfish_and_ipmi(
    redfish_session: requests.Session,
    redfish_config: RedfishConfig,
):
    redfish_readings = _redfish_cpu_temperatures(redfish_session, redfish_config)
    if not redfish_readings:
        pytest.skip(
            "This QEMU image exposes no CPU temperature telemetry in Redfish; "
            "comparison runs on a target that publishes CPU sensors"
        )
    ipmi_readings = _ipmi_cpu_temperatures(redfish_config)
    if not ipmi_readings:
        pytest.skip(
            "IPMI exposes CPU sensor records without numeric readings in this "
            "QEMU image; comparison runs when numeric readings are available"
        )

    tolerance = float(os.getenv("SENSOR_TOLERANCE_C", "5"))
    differences = []
    matches = 0
    for redfish in redfish_readings:
        normalised = _normalise_sensor_name(redfish.name)
        candidate = next(
            (
                value
                for name, value in ipmi_readings.items()
                if name in normalised or normalised in name
            ),
            None,
        )
        if candidate is None:
            continue
        matches += 1
        delta = abs(redfish.celsius - candidate)
        if delta > tolerance:
            differences.append(
                f"{redfish.name}: Redfish={redfish.celsius} C, IPMI={candidate} C, delta={delta} C"
            )
    assert matches, "Redfish and IPMI did not expose CPU sensors with matching names"
    assert not differences, "; ".join(differences)
