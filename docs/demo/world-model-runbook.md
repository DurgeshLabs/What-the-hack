# World model: local test runbook

Run these commands from the repository root after checking out
`what-the-hack/world-model`.

## 1. Install the normal development dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
pip install -r ai/requirements.txt
```

## 2. Verify feature extraction

This is the fastest check: it parses two ordinary flow rows, calculates every one of
the 37 features, and validates the result against the same production contract.

```bash
PYTHONPATH=.:backend pytest backend/tests/test_feature_extraction.py -q
```

Run the broader existing checks too:

```bash
PYTHONPATH=.:backend pytest tests/ml backend/tests -q
python ai/feature_engineering/validate_feature_schema.py
```

## 3. Train on real data

Download or generate a CICIDS2017 CSV, then run:

```bash
PYTHONPATH=.:backend python -m ai.training.train_world_model path/to/cicids.csv --epochs 15
```

The trainer accepts either raw CICIDS2017 headers or the app's normalized upload CSV.
It writes `ai/models/world_model.pt` locally. Do not commit this artifact.

## 4. Test the trained model in Python

```python
from ai.inference.forecast_engine import load_model, forecast
from ai.inference.contract import FEATURE_NAMES

model, checkpoint = load_model("ai/models/world_model.pt")
one_window = {name: 0 for name in FEATURE_NAMES}
one_window.update({"flow_count": 1, "packet_count": 1, "byte_count": 1})
result = forecast(model, checkpoint, [one_window] * checkpoint["seq_len"])
print(result)
```

This confirms the complete model path: checkpoint loading, ten-window history,
five-step forecast, MITRE stage output, and feature explanations.
