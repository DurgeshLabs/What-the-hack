#!/usr/bin/env bash
# Start the authorised local Zeek sensor and the complete Docker application in one terminal.
# macOS Docker Desktop cannot capture the host Wi-Fi interface itself, so Zeek remains a
# host process and Docker runs the dashboard/API/adapter together.
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$project_root"

if [[ $# -ne 1 ]]; then
  echo "Usage: WTH_ANALYST_PASSWORD='...' $0 <authorised-interface>" >&2
  echo "Find the interface with: networksetup -listallhardwareports" >&2
  exit 2
fi

if ! command -v zeek >/dev/null 2>&1; then
  echo "Zeek is not installed. On macOS: brew install zeek" >&2
  exit 1
fi

: "${WTH_ANALYST_PASSWORD:?Set WTH_ANALYST_PASSWORD to the local analyst password first}"
interface="$1"
export ZEEK_LOG_DIR="${ZEEK_LOG_DIR:-$HOME/zeek-live}"
mkdir -p "$ZEEK_LOG_DIR"

echo "Starting Zeek on $interface. Monitor only a network you own or are explicitly authorised to monitor."
(
  cd "$ZEEK_LOG_DIR"
  exec sudo zeek -i "$interface" LogAscii::use_json=T
) &
zeek_pid=$!

cleanup() {
  echo "Stopping local Zeek sensor …"
  sudo kill "$zeek_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

docker compose up -d --build --wait
docker compose exec backend python scripts/seed_demo_users.py
docker compose -f docker-compose.yml -f docker-compose.live.yml --profile live up --build live-adapter
