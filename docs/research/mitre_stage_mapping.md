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

## Training input

`python -m ai.training.train_world_model <csv>` accepts either the repository's
normalized upload CSV (`timestamp`, `src_ip`, …, `label`) or a raw CICIDS2017 CSV.
Raw CICIDS files are first passed through the existing dataset normalizer, then grouped
into the contract's 60-second windows. A real training dataset must contain more than
ten windows; the tiny demo replay is suitable for feature verification, not training.
