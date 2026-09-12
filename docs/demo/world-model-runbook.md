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

Download a labeled CICIDS2017 CSV, then run:

```bash
PYTHONPATH=.:backend python -m ai.training.train_world_model path/to/cicids.csv --epochs 15
```

The trainer accepts either raw CICIDS2017 headers or the app's normalized upload CSV.
It writes `ai/models/world_model.pt` locally. The repository includes one small
demo-trained checkpoint so a fresh clone can run the dashboard; do not overwrite it
with a new artifact unless you intend to version and review that training run.

### Compact public archive variant

If the downloaded archive contains `monday.csv` through `friday.csv` with decimal-IP
columns such as `Src IP dec` and short `mm:ss.s` timestamps, normalize it first:

```bash
PYTHONPATH=.:backend python -m ai.datasets.prepare_archive_training_data \
  /path/to/archive --out ai/datasets/cleaned/cicids2017_archive_clean.csv --stride 20
```

The cleaner converts decimal addresses, column aliases, malformed numeric values, and
label variants. Because this mirror omits the hour/day in its timestamps, it builds a
deterministic source-order replay timeline; use the original official timestamped CSVs
for final research metrics. Train the cleaned replay with:

```bash
PYTHONPATH=.:backend python -m ai.training.train_world_model \
  ai/datasets/cleaned/cicids2017_archive_clean.csv --epochs 15
```

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

## 5. Docker demo

The bundled artifact at `ai/models/world_model.pt` is mounted by Compose by default.
To use a different artifact, put it at that path or set this in the repository-root
`.env` before starting Compose:

```bash
WORLD_MODEL_CHECKPOINT=/app/ai/models/world_model.pt
docker compose up --build
```

The backend image installs `ai/requirements.txt`. If you keep a separate artifact
outside the repository, copy it into the repository's `ai/models/` directory before
starting Compose (the directory is mounted read-only into the backend):

```bash
cp /path/to/another-world-model.pt ai/models/world_model.pt
docker compose restart backend
```
