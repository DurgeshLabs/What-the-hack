from types import SimpleNamespace

from app.services.features import window_features
from app.services.ingestion import parse_csv_flows
from ai.inference.contract import FEATURE_NAMES, validate_features


def test_uploaded_flows_produce_the_37_feature_contract() -> None:
    csv = """timestamp,src_ip,dst_ip,src_port,dst_port,protocol,packets,bytes,duration_ms,flags,failed_conn_info,label
2026-08-28T18:00:00Z,192.168.1.5,192.168.1.10,1000,443,TCP,10,2000,50,SYN,SYN_NO_ACK,PortScan
2026-08-28T18:00:10Z,192.168.1.6,8.8.8.8,1001,53,UDP,2,120,20,NONE,NA,BENIGN
"""
    flows = [SimpleNamespace(**flow.__dict__) for flow in parse_csv_flows(csv).flows]
    values = window_features(flows, previous=None, earlier=[], window_seconds=60)
    public_values = {name: values[name] for name in FEATURE_NAMES}
    assert tuple(public_values) == FEATURE_NAMES
    assert validate_features(public_values) == public_values
