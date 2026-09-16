"""Send authorised Zeek connection metadata to What the Hack's live-ingestion API.

This program intentionally reads Zeek's *connection log* only.  It never reads a
packet capture or transmits packet payloads.  Run it only on a network/interface
you own or are explicitly authorised to monitor.

Example (after Docker Compose is healthy)::

    export WTH_ANALYST_PASSWORD='your analyst password'
    python3 -m ai.ingestion.zeek_live_adapter --log ~/zeek-live/conn.log
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_API = "http://127.0.0.1:8000/api/v1"
DEFAULT_EMAIL = "analyst@what-the-hack.local"


def _int(value: object, default: int = 0) -> int:
    """Zeek represents missing numbers as '-' in both ASCII and JSON log modes."""
    try:
        return max(0, int(float(str(value))))
    except (TypeError, ValueError):
        return default


def _optional_int(value: object) -> int | None:
    if value in (None, "", "-"):
        return None
    return _int(value)


def _flags(history: object) -> str | None:
    """Coarsely map Zeek connection history letters to the public CSV contract."""
    value = str(history or "")
    flags: list[str] = []
    for letter, flag in (("S", "SYN"), ("A", "ACK"), ("F", "FIN"), ("R", "RST"), ("P", "PSH")):
        if letter in value:
            flags.append(flag)
    return ",".join(flags) or None


def _connection_state(conn_state: object) -> str:
    value = str(conn_state or "").upper()
    if value in {"S0", "SH", "SHR"}:
        return "SYN_NO_ACK"
    if value.startswith("RST") or value == "REJ":
        return "RST_ABORT"
    return "CLEAN"


def zeek_record_to_flow(record: dict[str, Any]) -> dict[str, Any] | None:
    """Normalise one Zeek JSON ``conn.log`` record into the live API contract."""
    origin, responder = record.get("id.orig_h"), record.get("id.resp_h")
    timestamp = record.get("ts")
    if origin in (None, "", "-") or responder in (None, "", "-") or timestamp in (None, "", "-"):
        return None
    try:
        observed = datetime.fromtimestamp(float(timestamp), tz=timezone.utc).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError, OSError):
        return None
    duration = record.get("duration")
    duration_ms = None if duration in (None, "", "-") else _int(float(str(duration)) * 1000)
    return {
        "timestamp": observed,
        "src_ip": str(origin),
        "dst_ip": str(responder),
        "protocol": str(record.get("proto") or "OTHER").upper(),
        "packets": _int(record.get("orig_pkts")) + _int(record.get("resp_pkts")),
        "bytes": _int(record.get("orig_bytes")) + _int(record.get("resp_bytes")),
        "src_port": _optional_int(record.get("id.orig_p")),
        "dst_port": _optional_int(record.get("id.resp_p")),
        "duration_ms": duration_ms,
        "flags": _flags(record.get("history")),
        "failed_conn_info": _connection_state(record.get("conn_state")),
    }


class ApiClient:
    def __init__(self, api_base: str, email: str, password: str, timeout_seconds: float = 15.0):
        self.api_base = api_base.rstrip("/")
        self.email = email
        self.password = password
        self.timeout_seconds = timeout_seconds
        self.access_token = ""
        self.refresh_token = ""

    def _request(self, path: str, payload: dict[str, Any], token: str | None = None) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = Request(
            f"{self.api_base}{path}", data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:  # nosec B310 - operator supplied local API URL
            return json.loads(response.read().decode("utf-8"))

    def login(self) -> None:
        tokens = self._request("/auth/login", {"email": self.email, "password": self.password})
        self.access_token, self.refresh_token = tokens["access_token"], tokens["refresh_token"]

    def refresh(self) -> None:
        tokens = self._request("/auth/refresh", {"refresh_token": self.refresh_token})
        self.access_token, self.refresh_token = tokens["access_token"], tokens["refresh_token"]

    def send_flows(self, source_name: str, flows: list[dict[str, Any]]) -> dict[str, Any]:
        try:
            return self._request("/ingestion/live", {"source_name": source_name, "flows": flows}, self.access_token)
        except HTTPError as exc:
            if exc.code != 401:
                raise
            self.refresh()
            return self._request("/ingestion/live", {"source_name": source_name, "flows": flows}, self.access_token)


def tail_json_log(path: Path, from_start: bool):
    """Follow a JSON Zeek log and handle log rotation without using external packages."""
    handle = None
    inode: tuple[int, int] | None = None
    try:
        while True:
            try:
                stat = path.stat()
                current_inode = (stat.st_dev, stat.st_ino)
                if handle is None or inode != current_inode:
                    if handle:
                        handle.close()
                    handle = path.open("r", encoding="utf-8")
                    if not from_start:
                        handle.seek(0, os.SEEK_END)
                    inode = current_inode
                    from_start = True
                    print(f"Following Zeek metadata log: {path}", flush=True)
                line = handle.readline()
                if not line:
                    time.sleep(0.5)
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(event, dict):
                    yield event
            except FileNotFoundError:
                print(f"Waiting for Zeek to create {path} …", flush=True)
                time.sleep(1)
    finally:
        if handle:
            handle.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bridge authorised Zeek conn.log metadata to What the Hack.")
    parser.add_argument("--log", type=Path, default=Path.home() / "zeek-live" / "conn.log", help="Zeek JSON conn.log path")
    parser.add_argument("--api", default=DEFAULT_API, help="Backend API base URL")
    parser.add_argument("--email", default=DEFAULT_EMAIL, help="Analyst account email")
    parser.add_argument("--source", default="zeek-live", help="Name displayed for this live sensor")
    parser.add_argument("--batch-size", type=int, default=100, help="Flows per API batch (1–1000)")
    parser.add_argument("--flush-seconds", type=float, default=5.0, help="Maximum seconds before a partial batch is sent")
    parser.add_argument("--from-start", action="store_true", help="Replay existing JSON records rather than only following new events")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    password = os.environ.get("WTH_ANALYST_PASSWORD")
    if not password:
        print("Set WTH_ANALYST_PASSWORD to the analyst account password before starting the bridge.", file=sys.stderr)
        return 2
    if not 1 <= args.batch_size <= 1000:
        print("--batch-size must be between 1 and 1000", file=sys.stderr)
        return 2
    client = ApiClient(args.api, args.email, password)
    try:
        client.login()
    except (HTTPError, URLError, KeyError, json.JSONDecodeError) as exc:
        print(f"Could not sign in to {args.api}: {exc}", file=sys.stderr)
        return 1
    print("Signed in. Sending connection metadata only; press Ctrl-C to stop.", flush=True)
    batch: list[dict[str, Any]] = []
    last_flush = time.monotonic()
    try:
        for record in tail_json_log(args.log.expanduser(), args.from_start):
            flow = zeek_record_to_flow(record)
            if flow is not None:
                batch.append(flow)
            if batch and (len(batch) >= args.batch_size or time.monotonic() - last_flush >= args.flush_seconds):
                response = client.send_flows(args.source, batch)
                print(f"Sent {len(batch)} flows → source {str(response['traffic_source_id'])[:8]}; job {str(response['id'])[:8]}", flush=True)
                batch, last_flush = [], time.monotonic()
    except KeyboardInterrupt:
        print("\nStopping live bridge.", flush=True)
    except (HTTPError, URLError, KeyError, json.JSONDecodeError) as exc:
        print(f"Live bridge stopped because the API request failed: {exc}", file=sys.stderr)
        return 1
    if batch:
        try:
            response = client.send_flows(args.source, batch)
            print(f"Sent final {len(batch)} flows → source {str(response['traffic_source_id'])[:8]}", flush=True)
        except (HTTPError, URLError, KeyError, json.JSONDecodeError) as exc:
            print(f"Could not send final batch: {exc}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
