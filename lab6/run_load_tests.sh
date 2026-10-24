#!/usr/bin/env bash
set -euo pipefail

mode="${1:-public}"
users="${LOCUST_USERS:-10}"
spawn_rate="${LOCUST_SPAWN_RATE:-2}"
run_time="${LOCUST_RUN_TIME:-30s}"

mkdir -p reports

case "$mode" in
  public)
    prefix="reports/public_api"
    user_class="PublicApiUser"
    ;;
  openbmc)
    : "${OPENBMC_USERNAME:?Set OPENBMC_USERNAME}"
    : "${OPENBMC_PASSWORD:?Set OPENBMC_PASSWORD}"
    prefix="reports/openbmc_api"
    user_class="OpenBMCUser"
    ;;
  *)
    echo "Usage: $0 [public|openbmc]" >&2
    exit 2
    ;;
esac

locust -f locustfile.py "$user_class" \
  --headless \
  --users "$users" \
  --spawn-rate "$spawn_rate" \
  --run-time "$run_time" \
  --csv "$prefix" \
  --html "${prefix}.html" \
  --only-summary
