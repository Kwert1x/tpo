#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts/qemu runtime

if [[ ! -f "${OPENBMC_IMAGE:?Set OPENBMC_IMAGE}" ]]; then
  echo "OpenBMC image not found: $OPENBMC_IMAGE" >&2
  exit 1
fi

# The source image is mounted read-only.  QEMU receives a per-build writable
# copy so the original laboratory image is never modified.
cp "$OPENBMC_IMAGE" runtime/openbmc-work.mtd

if [[ -f runtime/qemu.pid ]] && kill -0 "$(cat runtime/qemu.pid)" 2>/dev/null; then
  echo "QEMU is already running"
  exit 0
fi

export JENKINS_NODE_COOKIE=dontKillMe
nohup qemu-system-arm \
  -m 256 \
  -M romulus-bmc \
  -nographic \
  -drive "file=runtime/openbmc-work.mtd,format=raw,if=mtd" \
  -net nic \
  -net user,hostfwd=:0.0.0.0:2222-:22,hostfwd=:0.0.0.0:2443-:443,hostfwd=udp:0.0.0.0:2623-:623,hostname=qemu \
  > artifacts/qemu/console.log 2>&1 &

echo $! > runtime/qemu.pid
echo "Started OpenBMC QEMU with PID $(cat runtime/qemu.pid)"
