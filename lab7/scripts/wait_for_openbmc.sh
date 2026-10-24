#!/usr/bin/env bash
set -euo pipefail

deadline=$((SECONDS + 420))
url="${OPENBMC_BASE_URL:?Set OPENBMC_BASE_URL}/redfish/v1/"

while (( SECONDS < deadline )); do
  if curl --silent --show-error --insecure \
      --user "${OPENBMC_USERNAME:?Set OPENBMC_USERNAME}:${OPENBMC_PASSWORD:?Set OPENBMC_PASSWORD}" \
      --output artifacts/qemu/redfish-root.json \
      --write-out '%{http_code}' \
      "$url" | grep -q '^200$'; then
    echo "OpenBMC Redfish API is ready at $url"
    exit 0
  fi
  if [[ -f runtime/qemu.pid ]] && ! kill -0 "$(cat runtime/qemu.pid)" 2>/dev/null; then
    echo "QEMU stopped before OpenBMC became ready" >&2
    exit 1
  fi
  sleep 5
done

echo "OpenBMC did not become ready within 420 seconds" >&2
exit 1
