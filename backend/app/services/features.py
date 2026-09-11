"""Contract-v1 feature extraction from a single persisted traffic window."""

from __future__ import annotations

from collections import Counter
import ipaddress
import math
from typing import Any, Iterable



def _entropy(values: Iterable[object]) -> float:
    counts = Counter(values)
    total = sum(counts.values())
    return -sum((count / total) * math.log2(count / total) for count in counts.values()) if total else 0.0


def window_features(
    flows: list[Any], previous: dict[str, float] | None, earlier: list[dict[str, float]], window_seconds: int,
) -> dict[str, float]:
    """Return the exact 37-feature inference contract for a non-empty window."""
    count = len(flows)
    if not count:
        raise ValueError("Cannot extract features for an empty window")
    packets, bytes_ = sum(flow.packet_count for flow in flows), sum(flow.byte_count for flow in flows)
    flags = [set((flow.tcp_flags or "").split(",")) for flow in flows]
    flag_count = lambda flag: sum(flag in value for value in flags)
    syn, ack = flag_count("SYN"), flag_count("ACK")
    durations = [flow.duration_ms or 0 for flow in flows]
    packet_sizes = [flow.byte_count / flow.packet_count if flow.packet_count else 0.0 for flow in flows]
    destination_ports = [flow.dst_port for flow in flows if flow.dst_port is not None]
    repeats = count - len({(flow.src_ip, flow.dst_ip, flow.dst_port) for flow in flows})
    inbound = sum(ipaddress.ip_address(flow.dst_ip).is_private for flow in flows)
    rate_packets, rate_bytes, rate_flows = packets / window_seconds, bytes_ / window_seconds, count / window_seconds
    baseline = earlier[-3:]
    mean_packets = sum(item["packet_count"] for item in baseline) / len(baseline) if baseline else None
    mean_syn = sum(item["_syn_count"] for item in baseline) / len(baseline) if baseline else None
    features = {
        "flow_count": count, "packet_count": packets, "byte_count": bytes_,
        "avg_packets_per_flow": packets / count, "avg_bytes_per_flow": bytes_ / count,
        "avg_duration_ms": sum(durations) / count, "packet_length_mean": bytes_ / packets if packets else 0.0,
        "packet_length_std": math.sqrt(sum((value - (sum(packet_sizes) / count)) ** 2 for value in packet_sizes) / count),
        "unique_src_ips": len({flow.src_ip for flow in flows}), "unique_dst_ips": len({flow.dst_ip for flow in flows}),
        "unique_src_ports": len({flow.src_port for flow in flows if flow.src_port is not None}), "unique_dst_ports": len(set(destination_ports)),
        "src_ip_entropy": _entropy(flow.src_ip for flow in flows), "dst_port_entropy": _entropy(destination_ports),
        "protocol_tcp_ratio": sum(flow.protocol == "TCP" for flow in flows) / count,
        "protocol_udp_ratio": sum(flow.protocol == "UDP" for flow in flows) / count,
        "protocol_icmp_ratio": sum(flow.protocol == "ICMP" for flow in flows) / count,
        "syn_ratio": syn / count, "ack_ratio": ack / count, "fin_ratio": flag_count("FIN") / count, "rst_ratio": flag_count("RST") / count,
        "syn_ack_ratio": syn / (ack + 1), "failed_conn_ratio": sum(flow.failed_connection is True for flow in flows) / count,
        "short_flow_ratio": sum(value < 100 for value in durations) / count,
        "inbound_outbound_ratio": inbound / (count - inbound + 1), "retry_rate": repeats / count,
        "packet_rate_per_sec": rate_packets, "byte_rate_per_sec": rate_bytes, "flow_rate_per_sec": rate_flows,
        "packet_burst_score": packets / (mean_packets + 1) if mean_packets is not None else 1.0,
        "syn_burst_score": syn / (mean_syn + 1) if mean_syn is not None else 1.0,
        "delta_packet_rate": rate_packets - previous["packet_rate_per_sec"] if previous else 0.0,
        "delta_byte_rate": rate_bytes - previous["byte_rate_per_sec"] if previous else 0.0,
        "delta_syn_ratio": syn / count - previous["syn_ratio"] if previous else 0.0,
        "delta_failed_conn_ratio": sum(flow.failed_connection is True for flow in flows) / count - previous["failed_conn_ratio"] if previous else 0.0,
        "delta_unique_dst_ports": len(set(destination_ports)) - previous["unique_dst_ports"] if previous else 0,
        "delta_packet_burst_score": 0.0, "_syn_count": syn,
    }
    if previous:
        features["delta_packet_burst_score"] = features["packet_burst_score"] - previous["packet_burst_score"]
    return features
