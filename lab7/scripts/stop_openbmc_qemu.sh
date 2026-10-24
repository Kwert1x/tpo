#!/usr/bin/env bash
set -euo pipefail

if [[ -f runtime/qemu.pid ]]; then
  pid="$(cat runtime/qemu.pid)"
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid"
    for _ in {1..20}; do
      kill -0 "$pid" 2>/dev/null || break
      sleep 1
    done
  fi
  rm -f runtime/qemu.pid
fi
