# World-model MITRE stage mapping

The world model never learns the mapping from a raw dataset label to an ATT&CK-style phase. `ai/inference/mitre_stage_map.py` owns that fixed mapping, so training and the prediction display cannot drift.

| CICIDS2017 label/family | World-model stage |
| --- | --- |
| `BENIGN` | Benign |
| `PortScan` / Reconnaissance | Reconnaissance |
| FTP/SSH Patator, web attacks, Heartbleed | Initial Access |
| Infiltration | Lateral Movement |
| Botnet | Command & Control |
| DoS / DDoS | Exfiltration / Impact |

The final bucket intentionally groups disruptive late-stage outcomes for this demo; it is not a claim that DoS is exfiltration.
