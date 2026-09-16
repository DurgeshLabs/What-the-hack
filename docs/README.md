# docs/

| Folder | Contents |
| --- | --- |
| `architecture/` | Scope lock, system workflow, database schema, world-model architecture. Start with `day-1-scope.md`. |
| `api/` | REST contract (`api-contracts.md`), the ML inference contract in prose (`ml-inference-contract.md`), and the generated JSON feature-schema contract. |
| `research/` | Forecasting formulation, precursor dynamics, and the CICIDS-to-MITRE stage mapping. |
| `demo/` | The 7-minute demo script, the world-model runbook, and the authorised Zeek live-ingestion runbook. |
| `devlog/` | Day-by-day setup and verification guides written as features landed. |
| `deliverables/` | Documents prepared for submission. |

## Start here

| I want to... | Read |
| --- | --- |
| Understand the product and its boundaries | `architecture/day-1-scope.md` |
| See the database tables | `architecture/database-schema.md` |
| Call or extend the REST API | `api/api-contracts.md` |
| Integrate with the ML model | `api/ml-inference-contract.md` |
| Understand how forecasting is defined | `research/forecasting_formulation.md` |
| Read the attack-stage labels | `research/mitre_stage_mapping.md` |
| Run the pipeline end to end | `devlog/day-4-ingestion.md`, `devlog/day-5-windows-and-docker.md` |
| Train or retrain the model | `demo/world-model-runbook.md` |
| Run the live sensor demo | `demo/live-zeek-ingestion.md` |
| Present the project | `demo/demo-script.md` |

`api/feature_schema_contract.json` is generated. Edit `ai/inference/contract.py` and run
`ai/feature_engineering/build_feature_schema_contract.py` instead of changing it by hand.
