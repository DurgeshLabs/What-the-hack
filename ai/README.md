# ai/ — machine learning workspace

Owner: Yash (AI/ML). Everything here is offline tooling plus the inference module the
backend imports. The wire contract is `docs/api/ml-inference-contract.md`; the machine
readable version is `docs/api/feature_schema_contract.json`.

| Folder | Purpose |
| --- | --- |
| `datasets/` | `download_cicids2017.py` (acquisition, checksum verification, synthetic generator, CICIDS2017 → `raw_flows` mapping), `prepare_archive_training_data.py`, and the bundled cleaned demo replay under `cleaned/`. |
| `feature_engineering/` | `build_feature_schema_contract.py` generates the JSON contract; `validate_feature_schema.py` stress-tests it; `labeled_windows.py` builds future-shifted training windows. |
| `training/` | `train_world_model.py` trains the PyTorch dynamics + risk-stage model. |
| `evaluation/` | `evaluate_models.py` compares the world model against a logistic-regression baseline. |
| `inference/` | `contract.py` is the single source of truth for the feature schema. `forecast_engine.py` runs the trained checkpoint, `fallback.py` is the dependency-free rule-based scorer, `mitre_stage_map.py` maps classes to MITRE-aligned stages. |
| `ingestion/` | `zeek_live_adapter.py` normalises Zeek `conn.log` metadata into the contract shape. |
| `models/` | `world_model.py` defines the architecture; `world_model.pt` is the small committed demo checkpoint. |

## The contract is generated, not written

Edit `ai/inference/contract.py`, then regenerate and commit the JSON:

```bash
python3 ai/feature_engineering/build_feature_schema_contract.py
```

Mirror any change in `backend/app/schemas/inference.py` in the same pull request. CI fails
if the committed JSON differs from what the generator produces.

## Forecasting rule

Every model here is trained with future-shifted labels: features from window `t` predict
whether an attack starts or escalates in `(t, t + horizon]`. A model that labels the
current window is detection, not forecasting, and does not belong in `training/`. See
`docs/research/forecasting_formulation.md`.

## Dependencies

The backend runs without any ML library, falling back to the rule-based scorer. Training
and checkpoint inference additionally need `ai/requirements.txt` (NumPy and PyTorch).

## What is committed, and what is not

Only two data artifacts are in git, each justified in its folder README:
`datasets/cleaned/cicids2017_archive_clean.csv` and `models/world_model.pt`. They exist so
a fresh clone can run the full demo without the 1.7 GB source archive. Everything else,
including raw downloads under `datasets/data/` and any new checkpoint, stays ignored.
Commit a `<model_name>.metadata.json` beside any future artifact.

## Common commands

```bash
python3 ai/datasets/download_cicids2017.py --help
python3 ai/datasets/download_cicids2017.py --offline-mock --out-dir ./ai/datasets/data

PYTHONPATH=.:backend python -m ai.training.train_world_model \
  ai/datasets/cleaned/cicids2017_archive_clean.csv --epochs 15
```

Full training and evaluation walkthrough: `docs/demo/world-model-runbook.md`.
