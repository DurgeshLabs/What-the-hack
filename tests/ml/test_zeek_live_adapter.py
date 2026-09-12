from ai.ingestion.zeek_live_adapter import zeek_record_to_flow


def test_zeek_connection_record_maps_to_normalized_live_flow():
    flow = zeek_record_to_flow({
        "ts": 1_726_000_000.5,
        "id.orig_h": "10.0.0.12",
        "id.resp_h": "8.8.8.8",
        "id.orig_p": 51000,
        "id.resp_p": 53,
        "proto": "udp",
        "orig_pkts": 2,
        "resp_pkts": 1,
        "orig_bytes": 190,
        "resp_bytes": 92,
        "duration": 0.125,
        "history": "D",
        "conn_state": "SF",
    })

    assert flow == {
        "timestamp": "2024-09-10T20:26:40.500000Z",
        "src_ip": "10.0.0.12",
        "dst_ip": "8.8.8.8",
        "protocol": "UDP",
        "packets": 3,
        "bytes": 282,
        "src_port": 51000,
        "dst_port": 53,
        "duration_ms": 125,
        "flags": None,
        "failed_conn_info": "CLEAN",
    }


def test_zeek_record_requires_timestamp_and_connection_addresses():
    assert zeek_record_to_flow({"ts": 1, "id.orig_h": "10.0.0.1"}) is None
