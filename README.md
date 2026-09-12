# What the Hack — AI-based Network Attack Forecasting

**SIH 2026 · Problem statement SIH26153 · National Technical Research Organisation (NTRO)**
**Theme: Blockchain & Cybersecurity · Category: Software**

An explainable early-warning system that forecasts likely cyber attacks from network-traffic
behaviour **before they fully materialise**. It groups recent traffic into short windows,
extracts behavioural features, predicts the risk of an attack in the next 1–5 minutes, and
presents ranked, human-readable reasons and recommended actions to a security analyst.

This is forecasting, not detection: the model is trained with future-shifted labels, so the
features of window `t` predict whether an attack starts or escalates in `(t, t + horizon]`.
See `docs/research/forecasting_formulation.md`.

## Project status

The **end-to-end demo product is complete**: authenticate → upload CSV traffic or connect an authorised local Zeek sensor → build 60-second feature windows → forecast risk and a MITRE stage → view explanations → save and inspect an alert.

| Area | Included now | Important limitation |
| --- | --- | --- |
| Backend | JWT/RBAC, CSV replay and authorised Zeek connection-metadata ingestion, 37-feature window extraction, forecast endpoint, persisted alerts, PostgreSQL migrations | Live batches rebuild windows in this MVP; production needs incremental stream processing |
| ML | PyTorch dynamics + risk-stage model, label/window pipeline, bundled checkpoint, logistic-regression comparison utility | The bundled replay has incomplete source timestamps, so its evaluation result is a demo smoke test, not a final benchmark |
| Frontend | Login, upload, Live sensor picker, dashboard charts, a single MITRE-aligned stage verdict, mapping guide, explanations, alerts list/detail, sign-out handling | The browser deliberately never handles raw packet payloads |
| Deployment | Docker Compose stack, health checks, demo accounts | Development defaults only; change secrets for any shared deployment |

## Included demo artifacts

A fresh clone contains the artifacts needed to run the demonstrated prediction path.

| File | Purpose |
| --- | --- |
| `ai/datasets/cleaned/cicids2017_archive_clean.csv` | 105,000-row normalized, labeled CICIDS2017-derived replay for local upload and training checks |
| `ai/models/world_model.pt` | Pre-trained PyTorch world-model checkpoint used by Docker Compose and the dashboard |

The source archive is intentionally excluded because it is approximately 1.7 GB.
The bundled replay and checkpoint let every teammate reproduce the UI demo without
downloading it. The bundled replay uses a deterministic source-order timeline because
its public archive variant omits complete capture timestamps; it is a demo artifact,
not evidence for final benchmark claims.

## Screenshot

The dashboard displays the observed traffic timeline alongside the five-step forecast.
In this bundled demo run, 143 feature windows were built from the replay and the local
world model forecast a peak risk of 78%.

![What the Hack dashboard showing the observed traffic chart and five-minute risk forecast](frontend/public/screenshots/dashboard-forecast.png)

## Repository layout

```text
.
├── frontend/        Next.js analyst dashboard (app/, components/, lib/, public/)
├── backend/         FastAPI API: app/{api,core,db,models,schemas,services}, alembic/, tests/
├── ai/              ML workspace: datasets/, preprocessing/, feature_engineering/, training/,
│                    evaluation/, inference/, models/, notebooks/
├── database/        Schema snapshots, seed notes, migration rules (Alembic lives in backend/)
├── tests/           ml/ (contract + invariant tests), backend/, integration/, frontend/
├── docs/            architecture/, api/, research/, demo/, devlog/, diagrams/
├── deployment/      docker/, compose/, scripts/ (bootstrap_backend.sh, run_tests.sh)
├── sample_data/     sample_flows_mini.csv — deterministic 3-phase replay sample
├── .github/         CI workflow, PR and issue templates
├── docker-compose.yml
├── .env.example
├── CONTRIBUTING.md
└── LICENSE
```

## Quick start

### Run the complete demo in Docker

```bash
git clone https://github.com/DurgeshLabs/What-the-hack.git
cd What-the-hack
cp .env.example .env
docker compose up --build
```

### If you downloaded a ZIP instead of cloning

Extract the current GitHub ZIP, open Terminal in the extracted `What-the-hack-main`
folder, then run the same two commands:

```bash
cp .env.example .env
docker compose up --build
```

The ZIP includes the cleaned replay and the trained checkpoint, so Git and the original
large CICIDS archive are not required. If Docker reports that ports `3000`, `5432`, or
`8000` are already in use, another local copy of the demo is running. Stop that copy from
its own project folder with `docker compose down`, then run the command above again. Do
not use `docker compose down -v` unless you intend to remove its local database.

| Service | URL |
| --- | --- |
| Frontend | http://127.0.0.1:3000 |
| Backend API docs | http://127.0.0.1:8000/docs |
| Health check | http://127.0.0.1:8000/api/v1/health |
| PostgreSQL | localhost:5432 (`what_the_hack` / `what_the_hack`) |

`docker compose down` stops the stack and keeps the database volume. Only use
`docker compose down -v` when you intend to delete local data.

If your browser does not resolve `localhost`, use `127.0.0.1` exactly as shown above.

### Seed local demo accounts

Open a second terminal while Compose is running:

```bash
docker compose exec backend python scripts/seed_demo_users.py
```

| Role | Email | Local development password |
| --- | --- | --- |
| Analyst (recommended) | `analyst@what-the-hack.local` | `AnalystPass123!` |
| Admin | `admin@what-the-hack.local` | `AdminPass123!` |
| Viewer | `viewer@what-the-hack.local` | `ViewerPass123!` |

These passwords are deliberately development-only. Change them and set a strong `JWT_SECRET_KEY` before exposing the service beyond your machine.

### Use the app

1. Open **http://127.0.0.1:3000/login** and sign in as the analyst.
2. Go to **Upload** and select `ai/datasets/cleaned/cicids2017_archive_clean.csv`. This bundled file has enough data for the world-model sequence and is the recommended first demo replay. The required columns are timestamp, source/destination address, protocol, packet count, and byte count; see [`sample_data/`](sample_data/) for the accepted shape.
3. Wait for the upload status to become `completed`. The service persists raw rows and builds 60-second traffic windows plus the 37-feature vectors.
4. Select **Open your live dashboard**. It shows observed traffic immediately.
5. The bundled `ai/models/world_model.pt` mounts automatically when Compose starts. Refresh the dashboard after upload to see the five-step forecast, the attack-stage verdict, its MITRE-aligned mapping guide, and feature explanations.
6. Click **Save as alert** to add the current forecast to the investigation queue. Open **Alerts** to view the stored risk, stage, ranked contributors, and recommended actions.

`sample_data/sample_flows_mini.csv` verifies upload/windowing but is intentionally too short to create the ten-window sequence required by the forecasting model.

### Optional: live local network telemetry

For an authorised personal/lab-network demonstration, the repository includes a Zeek
connection-log bridge. It tails Zeek's JSON `conn.log`, sends **metadata only** (time,
addresses, ports, protocol, packet/byte counts, duration and connection state) to the
protected live-ingestion endpoint, and opens the same forecast dashboard. It never sends
packet payloads. Full setup, safety boundary, and troubleshooting are in
[the live Zeek runbook](docs/demo/live-zeek-ingestion.md). Once the bridge is sending,
use **Live sensor** in the navigation to select its dashboard source.

On macOS, the quickest authorised demo is one terminal after Zeek is installed:

```bash
WTH_ANALYST_PASSWORD='AnalystPass123!' bash deployment/scripts/start_live_demo.sh en0
```

Replace `en0` with the interface confirmed by `networksetup -listallhardwareports`.
Docker runs the application and bridge; Zeek stays on the host because Docker Desktop
cannot observe the Mac's physical Wi-Fi interface directly.

### Live-score interpretation and false positives

Do not treat the dashboard percentage as a verdict that a PC, Wi-Fi connection, IP address,
or website is malicious. It is the current model's **attack-likeness risk score** for the
next five minutes, not a calibrated probability and not a confirmed incident. A healthy
personal computer can score highly because its real traffic distribution (software updates,
streaming, cloud synchronization, DNS, encrypted connections, or a busy shared Wi-Fi) differs
from the controlled CICIDS2017 lab traffic used to train the bundled checkpoint. That is a
normal form of dataset shift and must be investigated as a possible false positive.

For a demo, say: *“The system raised an early-warning score because these traffic features
were unlike its training baseline. We validate it with destination, endpoint, and identity
evidence before calling it an incident.”* The dashboard shows the contributing feature values
and IP/port evidence for this validation. It intentionally does **not** call an IP address or
website malicious from flow statistics alone.

#### How to improve the model responsibly

1. **Keep CICIDS2017 as the starting training set**, but use its original timestamped files,
   not only the bundled compact replay. It provides labelled benign traffic plus brute force,
   DoS/DDoS, web attack, infiltration, botnet, and scan scenarios.
2. **Evaluate on a different dataset before making claims.** Use CSE-CIC-IDS2018 as an
   external test set after mapping it into this repository's 37-feature contract. Do not mix
   the same capture into both training and test partitions.
3. **Collect authorised benign Zeek metadata from the target environment** (for example one
   to two weeks of normal home/lab activity), remove or protect personal identifiers, and use
   it to measure the false-positive rate and tune an alert threshold. Do not fine-tune the
   whole attack classifier on benign-only data: that would make it forget attack classes.
4. **Calibrate and gate alerts.** Fit Platt scaling or isotonic calibration on a labelled
   validation split, choose a threshold for an agreed false-positive rate, and display
   “review” rather than “critical” when the model is out of distribution.
5. **Add domain and endpoint corroboration.** Enrich permitted live logs with DNS/TLS-SNI,
   endpoint process and authentication evidence; retain human analyst review before response.

Recommended public sources: [official CICIDS2017](https://www.unb.ca/cic/datasets/ids-2017.html),
[official CSE-CIC-IDS2018](https://www.unb.ca/cic/datasets/ids-2018.html), and
[ToN_IoT](https://research.unsw.edu.au/projects/toniot-datasets) only when the intended
deployment is IoT/industrial traffic. Each non-CIC dataset needs an explicit normalizer and
label mapping before it can train this model; do not upload it blindly and expect valid scores.

### Reading the attack-stage forecast

The dashboard deliberately shows one **five-minute stage verdict** rather than repeating the
same stage label in every forecast row. The rows beneath it show risk by future minute. If the
model predicts a change of stage, the interface instead displays the transition point and the
new stage. A sustained stage means the model sees a continuing pattern, not five separate
incidents.

The six model classes are `Benign`, `Reconnaissance`, `Initial Access`, `Lateral Movement`,
`Command & Control`, and `Exfiltration / Impact`. These are transparent, coarse
CICIDS-to-MITRE-aligned progression categories—not verified ATT&CK techniques. The analyst
must validate a forecast using endpoint, identity, and packet-level evidence. The exact label
mapping is in [docs/research/mitre_stage_mapping.md](docs/research/mitre_stage_mapping.md).

### Option B — local development

```bash
docker compose up -d db                      # PostgreSQL only
./deployment/scripts/bootstrap_backend.sh    # venv, deps, migrations, demo users
cd backend && PYTHONPATH=. .venv/bin/uvicorn app.main:app --reload
```

In a second terminal:

```bash
cd frontend && cp .env.example .env.local && npm install && npm run dev
```

Demo accounts are created by `backend/scripts/seed_demo_users.py` (roles `admin`,
`analyst`, `viewer`). The built-in demo passwords are accepted only while
`ENVIRONMENT=development`; anywhere else the script refuses to run until
`DEMO_ADMIN_PASSWORD`, `DEMO_ANALYST_PASSWORD`, and `DEMO_VIEWER_PASSWORD` are set.
Likewise the backend refuses to start outside development with the default
`JWT_SECRET_KEY` or one shorter than 32 characters.

### Train a model artifact

To retrain the bundled model from the bundled replay:

```bash
PYTHONPATH=.:backend python -m ai.training.train_world_model \
  ai/datasets/cleaned/cicids2017_archive_clean.csv --epochs 15
```

This replaces `ai/models/world_model.pt`. Restart the backend after training.
For final research, pass original timestamped CICIDS files instead; full preparation,
training, and evaluation instructions are in [the model runbook](docs/demo/world-model-runbook.md).

## Tests

```bash
./deployment/scripts/run_tests.sh            # pytest over backend/tests and tests/
./deployment/scripts/run_tests.sh backend/tests
./deployment/scripts/run_tests.sh tests/ml
cd frontend && npm run build
```

`tests/ml/test_tier5_adversarial_coverage.py` is ML work in progress and is skipped in CI
until it collects.

### Verify the bundled model

After cloning, confirm the checkpoint loads before opening the demo:

```bash
docker compose exec backend python -c "from ai.inference.forecast_engine import load_model; _, checkpoint = load_model('/app/ai/models/world_model.pt'); print('checkpoint ready:', checkpoint['seq_len'], 'history windows')"
```

The expected output is `checkpoint ready: 10 history windows`. Docker Compose mounts
this same artifact automatically at `/app/ai/models/world_model.pt`.

### Common local-demo fixes

| What you see | What to do |
| --- | --- |
| Browser cannot open `localhost` | Use `http://127.0.0.1:3000` and confirm `docker compose ps` shows both frontend and backend as running. |
| `401 Unauthorized` after switching tabs | Sign out and sign in again. A backend restart invalidates existing development tokens. |
| `403 Forbidden for /ingestion/upload` | Sign in with the **analyst** account, then rebuild/restart with `docker compose up --build` so the latest API permissions are running. |
| `409 Conflict` while uploading | The same file is already being processed or was already accepted. Return to the dashboard; uploads are idempotent in the current build. |
| Dashboard says `Artifact offline` | Run `git pull`, then `docker compose up --build`; use the verification command above to confirm the checkpoint is mounted. |
| Forecast panel is empty | Upload the bundled replay, which produces 143 windows. The small sample CSV does not reach the model's 10-window history requirement. |

### Dataset integrity

The checked-in replay is intentionally small enough to clone and share. Its SHA-256 is
`b513721d394229b03816d3010cf120f5f0f20ec7131821f54b9cb1d2331111ca`; verify it with:

```bash
shasum -a 256 ai/datasets/cleaned/cicids2017_archive_clean.csv
```

The checkpoint SHA-256 is
`7dddd4f26842928241eef023c0b37593270bfc32bebd53129e734ca090b5819d`.

## Architecture

```text
CSV replay or authorised Zeek conn.log → Ingestion API → raw_flows → Window builder → traffic_windows
   → 37-feature extraction → window_features → PyTorch world model + risk-stage head
   → predictions → Alert engine + explanations → alerts → Dashboard APIs → Next.js dashboard
   → Analyst acknowledges → alert_events, audit_logs
```

| Layer | Choice |
| --- | --- |
| Frontend | Next.js, React, Tailwind CSS |
| Backend | FastAPI, SQLAlchemy 2, Alembic, Pydantic |
| Database | PostgreSQL 16 |
| ML | PyTorch world model + risk-stage head, logistic-regression comparison, feature contribution ranking |
| Auth | JWT + role-based access control (`admin`, `analyst`, `viewer`) |
| Deployment | Docker Compose; CPU-only, no paid APIs |

Details: `docs/architecture/`, `docs/api/api-contracts.md`, `docs/architecture/database-schema.md`.

## Roadmap

- **MVP**: login, CSV upload/replay, windowing, feature extraction, one forecasting model,
  risk score, dashboard with alerts, one alert detail page with explanation.
- **Strong**: near-real-time replay, attack-type classification, SHAP panel, threshold
  tuning, host analytics, alert status workflow, model comparison, audit logs.
- **Winning**: true next-window labels, lead-time visualisation, detection-vs-forecasting
  comparison, uncertainty handling, attack progression timeline, recommendations,
  multi-dataset benchmarking.
- **Future (not for SIH)**: real enterprise traffic, automated firewall rules, multi-tenant
  SOC, distributed streaming, federated learning, adversarially robust sequence models.

## Security

JWT auth with Argon2 password hashing and refresh-token revocation on logout, RBAC on every
protected route, Pydantic validation, upload size and type limits, duplicate-upload
rejection, rate limiting on login and upload, CORS locked to the frontend origin, a
database-aware health check, and a startup guard that refuses weak JWT secrets outside
development. Still future work for production: HTTPS termination, Redis-backed rate
limits across workers, and secret rotation.

## Dataset, model, and evaluation honesty

The bundled replay is CICIDS2017-derived and includes attack labels for local training
and demonstration. It is not the original official timestamped capture export, so its
chronological final test partition can be class-skewed. Do not claim its local 100% binary
F1 smoke-test result as final research accuracy. For a defensible final benchmark, train
and evaluate with original timestamped CICIDS2017 files using a split where both benign and
attack windows appear in each test fold. Synthetic replay data is for UI verification only,
never as accuracy evidence.

### First-time setup

```bash
git clone https://github.com/DurgeshLabs/What-the-hack.git
cd What-the-hack
git checkout dev
```

Then follow **Quick start** above for your area. Backend and ML people need Python 3.12
and PostgreSQL (Docker), frontend people need Node 20.

### Daily workflow

1. **Pick a task.** Take an issue from the GitHub project board (Backlog -> This Week -> In
   Progress -> Blocked -> Review -> Ready for Integration -> Done). If there is no issue,
   create one with the *Feature / task* template and label it `frontend`, `backend`, `ml`,
   `docs`, or `demo`.
2. **Branch from `dev`.**
   ```bash
   git checkout dev && git pull
   git checkout -b feature/<area>-<topic>      # e.g. feature/frontend-alert-detail, feature/ml-xgboost-baseline
   ```
   Use `fix/<topic>` for bug fixes and `docs/<topic>` for documentation-only changes.
3. **Work in your folder.** Keep changes inside the area you own. If you must touch
   another area (for example the backend needs a new field from ML), open an issue and
   tag the owner first.
4. **Commit small, with a prefix.** `feat:`, `fix:`, `docs:`, `refactor:`, `test:`,
   `chore:`. Example: `feat: add alert detail API`.
5. **Run the checks before pushing.**
   ```bash
   ./deployment/scripts/run_tests.sh            # Python: backend + ML
   cd frontend && npm run build                 # frontend type-check and build
   ```
6. **Open a pull request against `dev`.** Fill in the template: what changed, screenshots
   for UI, test status, known limitations. Link the issue with `Closes #<number>`.
7. **Get one review.** At least one teammate approves before merging. Reviewers check that
   the contract docs still match the code and that nothing hard-codes secrets or paths.
8. **Merge and delete the branch.** `dev` is integrated end to end every two or three days;
   `main` is fast-forwarded from `dev` only after the full demo flow works.

### How to push your changes, by role

Every role follows the same shape: branch from `dev`, work in your folder, run your
checks, push, open a pull request against `dev`. The details differ per area.

#### Frontend (Adarsh)

```bash
git checkout dev && git pull
git checkout -b feature/frontend-<screen>          # e.g. feature/frontend-alert-detail
cd frontend && npm install && cp .env.example .env.local
npm run dev                                        # http://localhost:3000, backend on :8000
```

Work in `frontend/app` (pages), `frontend/components`, and `frontend/lib/api.ts` (typed
API calls; response shapes come from `docs/api/api-contracts.md`). Before pushing:

```bash
npm test && npm run build                          # type-check, then production build
git add frontend
git commit -m "feat: add alert detail page"
git push -u origin feature/frontend-alert-detail
```

Open the PR against `dev` with screenshots of every new or changed screen, and note the
empty, loading, and error states you handled.

#### Backend and database (Shreya)

```bash
git checkout dev && git pull
git checkout -b feature/backend-<topic>            # e.g. feature/backend-alerts-api
docker compose up -d db
./deployment/scripts/bootstrap_backend.sh          # venv, deps, migrations, demo users
cd backend && PYTHONPATH=..:. .venv/bin/uvicorn app.main:app --reload
```

Work in `backend/app` (routes in `api/v1/routes`, logic in `services`, Pydantic in
`schemas`, ORM in `models`). Schema changes get a new revision:

```bash
cd backend && .venv/bin/alembic revision -m "add alerts table"   # then edit the file
.venv/bin/alembic upgrade head
```

Before pushing:

```bash
./deployment/scripts/run_tests.sh backend/tests    # unit + HTTP tests on SQLite
cd backend && PYTHONPATH=. .venv/bin/python ../database/schema/export_schema.py   # if models changed
git add backend database docs/api
git commit -m "feat: add alerts list and detail API"
git push -u origin feature/backend-alerts-api
```

Update `docs/api/api-contracts.md` in the same PR whenever a response shape changes.

#### AI/ML and data (Yash)

```bash
git checkout dev && git pull
git checkout -b feature/ml-<topic>                 # e.g. feature/ml-xgboost-baseline
python3 -m venv backend/.venv && backend/.venv/bin/pip install -r backend/requirements.txt pytest jsonschema pandas numpy
```

Work in `ai/` (`preprocessing`, `feature_engineering`, `training`, `evaluation`,
`inference`) and `tests/ml`. Raw datasets go under `ai/datasets/data/` and model binaries
under `ai/models/`; both are git-ignored, commit only small metadata JSON. If the feature
contract changes:

```bash
# edit ai/inference/contract.py, bump CONTRACT_VERSION, then
backend/.venv/bin/python ai/feature_engineering/build_feature_schema_contract.py
# and mirror the change in backend/app/schemas/inference.py
```

Before pushing:

```bash
./deployment/scripts/run_tests.sh tests/ml backend/tests/test_inference_schemas.py
git add ai tests/ml docs/api docs/research
git commit -m "feat: train XGBoost baseline with next-window labels"
git push -u origin feature/ml-xgboost-baseline
```

The PR must include the metrics table (precision, recall, F1, ROC-AUC, PR-AUC, lead time)
and say which dataset split produced it.

#### UI/UX, QA, and documentation (Kshitij)

```bash
git checkout dev && git pull
git checkout -b docs/<topic>                       # e.g. docs/user-guide, or fix/<bug> for a bug you fixed
```

Wireframes and exports go in `docs/diagrams/`, test scenarios in `tests/integration/`
(Markdown checklists are fine until they become code), the user guide and demo notes in
`docs/demo/`. For a bug you found but cannot fix, open an issue with the *Bug report*
template and the `bug` label; add `urgent` if it blocks the demo. Before pushing:

```bash
./deployment/scripts/run_tests.sh                  # only if you touched code
git add docs tests/integration
git commit -m "docs: add analyst user guide"
git push -u origin docs/user-guide
```

#### DevOps, integration, and presentation (Arnav)

```bash
git checkout dev && git pull
git checkout -b chore/<topic>                      # e.g. chore/compose-redis, chore/ci-postgres
cp .env.example .env
docker compose up --build                          # full stack: db, backend, frontend
```

Work in `deployment/`, `docker-compose.yml`, the two Dockerfiles, and `.github/`. Before pushing:

```bash
docker compose config --quiet                      # compose file validates
docker compose up --build -d && curl -s localhost:8000/api/v1/health && docker compose down
./deployment/scripts/run_tests.sh
git add deployment docker-compose.yml backend/Dockerfile frontend/Dockerfile .github
git commit -m "chore: add redis service for background jobs"
git push -u origin chore/compose-redis
```

Run `./deployment/scripts/github_setup.sh` once (needs the GitHub CLI and admin rights)
to create the issue labels and protect `main` and `dev`.

#### Team lead (Durgesh)

Reviews and merges. To integrate `dev` into `main` after the end-to-end check:

```bash
git checkout dev && git pull
./deployment/scripts/run_tests.sh && (cd frontend && npm test && npm run build)
git checkout main && git pull
git merge --ff-only dev
git push origin main
```

If `--ff-only` refuses, someone pushed to `main` directly; merge `main` into `dev` first,
then retry.

### Rules that keep the demo safe

- Never commit `.env`, datasets, model binaries, or `node_modules`. `.gitignore` already
  blocks them; check `git status` before committing.
- Never edit an Alembic migration that has reached a shared database. Add a new one.
- Never change `docs/api/feature_schema_contract.json` by hand. Edit
  `ai/inference/contract.py`, regenerate, bump the version, and update
  `backend/app/schemas/inference.py` in the same PR.
- Never push directly to `main`.
- Every new API route, parser, feature calculator, or screen ships with a test.
- If you are blocked for more than half a day, move the card to *Blocked* and say so in
  the standup: what you finished, what you are doing today, what is blocking you.

### Where to look first

| I want to... | Read |
| --- | --- |
| Understand the product and its boundaries | `docs/architecture/day-1-scope.md` |
| See the database tables | `docs/architecture/database-schema.md` |
| Call or extend the REST API | `docs/api/api-contracts.md` |
| Integrate with the ML model | `docs/api/ml-inference-contract.md` |
| Run the pipeline end to end | `docs/devlog/day-4-ingestion.md`, `docs/devlog/day-5-windows-and-docker.md` |
| Prepare the demo | `docs/demo/demo-script.md` |
| Branch, commit, and PR rules in full | `CONTRIBUTING.md` |

## Team and ownership

See `CONTRIBUTING.md` for branch strategy (`main` stable, `dev` integration, feature
branches), commit conventions, PR checklist, labels, and the ownership/backup matrix.

## License

MIT — see `LICENSE`.
