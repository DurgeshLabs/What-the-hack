# World Model Architecture

## Purpose

What the Hack forecasts whether an attack is likely to emerge during the next five 60-second traffic windows. It uses behavioural features from uploaded network-flow CSV files and reports the forecast with an ATT&CK-style stage and ranked reasons.

## Data path

1. The upload API validates each flow and stores it in `raw_flows`.
2. The window builder groups flows into 60-second `traffic_windows`.
3. Feature extraction writes the 37 v1 contract values to `window_features`. Volume, protocol mix, TCP health, diversity, momentum, and deltas all use deterministic formulas.
4. Training maps CICIDS labels to six demo stages. For each window at time `t`, the risk label asks whether a non-benign stage appears in `(t, t + 5]`; it therefore cannot leak the current label into the prediction.
5. `DynamicsModel` consumes ten normalized windows and predicts the next feature vector. `RiskStageHead` scores each predicted vector for risk and stage. The forecast engine rolls the state forward five times.

## Training and evaluation

The trainer accepts normalized upload CSVs and raw CICIDS2017 CSVs. The dataset adapter normalizes raw CICIDS rows before windowing. Each checkpoint stores feature names, feature schema version, sequence length, and normalization statistics.

The evaluator makes a chronological train/test split. It trains logistic regression as the benchmark baseline, then measures the world model on the same held-out period. It prints precision, recall, F1, false-positive rate, and support. Results must be generated from a real dataset and included in the final submission; this project does not claim metrics before that run.

## Serving path

The backend exposes `/api/v1/analytics/overview` for persisted traffic and features. `/api/v1/analytics/forecast` loads the artifact named by `WORLD_MODEL_CHECKPOINT`, fetches the latest ten feature windows for the selected source, and returns five risks, stages, and gradient attributions. If the artifact, dependencies, or required history are unavailable, it returns a clear HTTP error rather than a fabricated forecast. The dashboard renders only API data and retains empty states for unavailable data.

## Safety and limits

The model expects the exact v1 feature order. The API rejects invalid feature values. The MITRE mapping is a fixed lookup, not a learned security claim. The UI should label untrained or unavailable model states clearly. CICIDS labels are benchmark annotations and do not prove coverage of a production network.
