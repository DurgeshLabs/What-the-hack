"""Build model-ready, labeled 60-second windows from uploaded-flow CSV exports."""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import ipaddress
from pathlib import Path
import sys
from typing import Iterable

import numpy as np

from ai.inference.contract import FEATURE_NAMES
from ai.inference.mitre_stage_map import risk_for_label, stage_for_label


@dataclass(frozen=True)
class LabeledWindows:
    features: np.ndarray
    risk_labels: np.ndarray
    stage_labels: np.ndarray


def forecasting_labels(stages: np.ndarray, horizon_windows: int = 5) -> tuple[np.ndarray, np.ndarray]:
    """Labels at t: whether an attack appears in (t, t + K], plus first stage.

    This deliberately excludes the current window to prevent same-window leakage.
    """
    risk, next_stage = np.zeros(len(stages), dtype=np.float32), np.zeros(len(stages), dtype=np.int64)
    for index in range(len(stages)):
        future = stages[index + 1:index + 1 + horizon_windows]
        attacks = future[future != 0]
        if len(attacks):
            risk[index], next_stage[index] = 1.0, attacks[0]
    return risk, next_stage


def _entropy(values: Iterable[object]) -> float:
    counts = Counter(values)
    total = sum(counts.values())
    if not total: return 0.0
    return float(-sum((count / total) * np.log2(count / total) for count in counts.values()))


def _floor(value: datetime, seconds: int) -> datetime:
    timestamp = value.astimezone(timezone.utc).timestamp()
    return datetime.fromtimestamp(int(timestamp // seconds) * seconds, tz=timezone.utc)


def _features(flows: list[object], previous: dict[str, float] | None, past: list[dict[str, float]], window_seconds: int) -> dict[str, float]:
    count = len(flows)
    packets = sum(flow.packet_count for flow in flows)
    bytes_ = sum(flow.byte_count for flow in flows)
    flags = [set((flow.tcp_flags or "").split(",")) for flow in flows]
    has_flag = lambda flag: sum(flag in value for value in flags)
    failed = sum(flow.failed_connection is True for flow in flows)
    flow_keys = [(flow.src_ip, flow.dst_ip, flow.dst_port) for flow in flows]
    repeated = count - len(set(flow_keys))
    durations = [flow.duration_ms or 0 for flow in flows]
    packet_sizes = [flow.byte_count / flow.packet_count if flow.packet_count else 0 for flow in flows]
    protocol = lambda name: sum(flow.protocol == name for flow in flows) / count
    inbound = sum(ipaddress.ip_address(flow.dst_ip).is_private for flow in flows)
    outbound = count - inbound
    syn = has_flag("SYN")
    packet_rate, byte_rate, flow_rate = packets / window_seconds, bytes_ / window_seconds, count / window_seconds
    baseline = past[-3:]
    prior_packets = np.mean([value["packet_count"] for value in baseline]) if baseline else None
    prior_syn = np.mean([value["syn_count"] for value in baseline]) if baseline else None
    result = {
        "flow_count": count, "packet_count": packets, "byte_count": bytes_,
        "avg_packets_per_flow": packets / count, "avg_bytes_per_flow": bytes_ / count,
        "avg_duration_ms": float(np.mean(durations)), "packet_length_mean": bytes_ / packets if packets else 0.0,
        "packet_length_std": float(np.std(packet_sizes)), "unique_src_ips": len({flow.src_ip for flow in flows}),
        "unique_dst_ips": len({flow.dst_ip for flow in flows}), "unique_src_ports": len({flow.src_port for flow in flows if flow.src_port is not None}),
        "unique_dst_ports": len({flow.dst_port for flow in flows if flow.dst_port is not None}), "src_ip_entropy": _entropy(flow.src_ip for flow in flows),
        "dst_port_entropy": _entropy(flow.dst_port for flow in flows if flow.dst_port is not None),
        "protocol_tcp_ratio": protocol("TCP"), "protocol_udp_ratio": protocol("UDP"), "protocol_icmp_ratio": protocol("ICMP"),
        "syn_ratio": syn / count, "ack_ratio": has_flag("ACK") / count, "fin_ratio": has_flag("FIN") / count, "rst_ratio": has_flag("RST") / count,
        "syn_ack_ratio": syn / (has_flag("ACK") + 1), "failed_conn_ratio": failed / count, "short_flow_ratio": sum(value < 100 for value in durations) / count,
        "inbound_outbound_ratio": inbound / (outbound + 1), "retry_rate": repeated / count,
        "packet_rate_per_sec": packet_rate, "byte_rate_per_sec": byte_rate, "flow_rate_per_sec": flow_rate,
        "packet_burst_score": packets / (prior_packets + 1) if prior_packets is not None else 1.0,
        "syn_burst_score": syn / (prior_syn + 1) if prior_syn is not None else 1.0,
        "delta_packet_rate": packet_rate - previous["packet_rate_per_sec"] if previous else 0.0,
        "delta_byte_rate": byte_rate - previous["byte_rate_per_sec"] if previous else 0.0,
        "delta_syn_ratio": syn / count - previous["syn_ratio"] if previous else 0.0,
        "delta_failed_conn_ratio": failed / count - previous["failed_conn_ratio"] if previous else 0.0,
        "delta_unique_dst_ports": len({flow.dst_port for flow in flows if flow.dst_port is not None}) - previous["unique_dst_ports"] if previous else 0,
        "delta_packet_burst_score": 0.0,
        "syn_count": syn,
    }
    if previous: result["delta_packet_burst_score"] = result["packet_burst_score"] - previous["packet_burst_score"]
    return result


def build_labeled_windows(csv_path: str | Path, window_seconds: int = 60) -> LabeledWindows:
    """Parse the repository's upload CSV format and produce the 37 contract features.

    A CSV must contain ``label`` in addition to the normal upload columns. One
    window's target is its most severe contained label; training shifts that target
    one window into the future, preventing same-window label leakage.
    """
    backend_root = str(Path(__file__).resolve().parents[2] / "backend")
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)
    from app.services.ingestion import parse_csv_flows  # backend parser is the input contract

    content = Path(csv_path).read_text(encoding="utf-8-sig")
    # CICIDS2017's raw CSV uses columns such as "Source IP" and "Timestamp".
    # Reuse the project mapper rather than maintaining a second set of conversions.
    headers = set(next(csv.reader([content.splitlines()[0]]), []))
    if "timestamp" not in headers and "Timestamp" in headers:
        from ai.datasets.download_cicids2017 import map_cicids_to_raw_flows
        import pandas as pd
        normalized = map_cicids_to_raw_flows(pd.read_csv(csv_path, low_memory=False))
        content = normalized.to_csv(index=False)
    parsed = parse_csv_flows(content)
    if not parsed.flows: raise ValueError("No valid flows were parsed from CSV.")
    buckets: dict[datetime, list[object]] = defaultdict(list)
    for flow in parsed.flows: buckets[_floor(flow.observed_at, window_seconds)].append(flow)
    feature_rows, risks, stages, previous, past = [], [], [], None, []
    for start in sorted(buckets):
        flows = buckets[start]
        values = _features(flows, previous, past, window_seconds)
        labels = [flow.extra_json.get("label", "BENIGN") for flow in flows]
        stage = max(stage_for_label(label) for label in labels)
        feature_rows.append([values[name] for name in FEATURE_NAMES])
        risks.append(float(stage != 0)); stages.append(stage)
        previous = values; past.append(values)
    stage_values = np.asarray(stages, dtype=np.int64)
    risk_values, future_stages = forecasting_labels(stage_values)
    return LabeledWindows(np.asarray(feature_rows, dtype=np.float32), risk_values, future_stages)
