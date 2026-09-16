# ai/models

`world_model.pt` is the small, committed demo checkpoint used by Docker Compose so a fresh
clone can run the complete prediction flow without retraining. It was trained from the bundled
CICIDS2017-derived replay and is suitable for demonstration only; see the root README for its
evaluation limitation.

Other, potentially large model artifacts remain ignored. Store a
`<model_name>.metadata.json` next to any future artifact with its model type, dataset,
feature-set version, metrics, and training date.
