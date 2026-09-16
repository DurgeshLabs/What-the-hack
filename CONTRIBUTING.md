# Contributing

This repository is the single integration point for the six-member team. Keep it boring
and predictable so the demo build never breaks.

- [Who owns what](#who-owns-what)
- [First-time setup](#first-time-setup)
- [Branches](#branches)
- [Daily workflow](#daily-workflow)
- [How to push your changes, by role](#how-to-push-your-changes-by-role)
- [Commit messages](#commit-messages)
- [Pull requests](#pull-requests)
- [Issues and labels](#issues-and-labels)
- [Rules that keep the demo safe](#rules-that-keep-the-demo-safe)
- [Naming conventions](#naming-conventions)
- [Environment and secrets](#environment-and-secrets)
- [Tests](#tests)

## Who owns what

| Member | Name | Owns | Works mostly in | Backup |
| --- | --- | --- | --- | --- |
| 1 | Durgesh | Team lead: scope, architecture, integration decisions, final PPT story | `docs/`, reviews everywhere | Arnav |
| 2 | Adarsh | Frontend: login, dashboard, alerts, upload and admin pages | `frontend/` | Kshitij |
| 3 | Shreya | Backend: APIs, auth, ingestion, windows, predictions, alerts, migrations | `backend/`, `database/` | Yash |
| 4 | Yash Bhanushali | AI/ML and data: datasets, features, labels, model, evaluation, inference | `ai/`, `tests/ml/`, `docs/research/` | Shreya |
| 5 | Kshitij | UI/UX, QA, documentation: wireframes, test cases, user guide, demo notes | `docs/`, `tests/` | Adarsh |
| 6 | Arnav | DevOps, integration, presentation: Docker, deployment, demo build, backup video | `deployment/`, `.github/` | Durgesh |

No critical knowledge lives with one person. Durgesh and Arnav can both run the full
stack, Shreya and Yash both understand the inference contract, Adarsh and Kshitij both
know the demo flow.

`.github/CODEOWNERS` turns this table into automatic review requests.

## First-time setup

```bash
git clone https://github.com/DurgeshLabs/What-the-hack.git
cd What-the-hack
git checkout dev
```

Then follow **Quick start** in the [README](README.md) for your area. Backend and ML need
Python 3.12 and Docker for PostgreSQL; frontend needs Node 20.

## Branches

| Branch | Purpose |
| --- | --- |
| `main` | Stable, demo-ready. Only fast-forward merges from `dev` after a full end-to-end check. |
| `dev` | Integration branch. All feature branches merge here through pull requests. |
| `feature/<area>-<topic>` | New work, e.g. `feature/frontend-alert-detail`, `feature/ml-xgboost-baseline`. |
| `fix/<topic>` | Bug fixes, e.g. `fix/upload-parser`. |
| `docs/<topic>` | Documentation-only changes. |
| `chore/<topic>` | Build, deployment, and CI changes. |

Always start from `dev`:

```bash
git checkout dev && git pull
git checkout -b feature/<area>-<topic>
```

## Daily workflow

1. **Pick a task.** Take an issue from the project board (Backlog → This Week → In
   Progress → Blocked → Review → Ready for Integration → Done). If there is no issue,
   create one with the *Feature / task* template and label it `frontend`, `backend`,
   `ml`, `docs`, or `demo`.
2. **Branch from `dev`** using the naming above.
3. **Work in your folder.** If you must touch another area, open an issue and tag the
   owner first.
4. **Commit small,** with a prefix.
5. **Run the checks** before pushing (see your role below).
6. **Open a pull request against `dev`.** Link the issue with `Closes #<number>`.
7. **Get one review.** Reviewers check that the contract docs still match the code and
   that nothing hard-codes secrets or paths.
8. **Merge and delete the branch.** `dev` is integrated end to end every two or three
   days; `main` is fast-forwarded from `dev` only after the full demo flow works.

## How to push your changes, by role

Every role follows the same shape: branch from `dev`, work in your folder, run your
checks, push, open a pull request against `dev`. The details differ per area.

### Frontend — Adarsh

```bash
git checkout dev && git pull
git checkout -b feature/frontend-<screen>          # e.g. feature/frontend-alert-detail
cd frontend && npm install && cp .env.example .env.local
npm run dev                                        # http://127.0.0.1:3000, backend on :8000
```

Work in `frontend/app` (pages), `frontend/components`, and `frontend/lib/api.ts` (typed
API calls; response shapes come from `docs/api/api-contracts.md`). Before pushing:

```bash
npm test && npm run build                          # type-check, then production build
git add frontend
git commit -m "feat: add alert detail page"
git push -u origin feature/frontend-alert-detail
```

Attach screenshots of every new or changed screen to the PR, and say which empty,
loading, and error states you handled.

### Backend and database — Shreya

```bash
git checkout dev && git pull
git checkout -b feature/backend-<topic>            # e.g. feature/backend-alerts-api
docker compose up -d db
./deployment/scripts/bootstrap_backend.sh          # venv, deps, migrations, demo users
cd backend && PYTHONPATH=..:. .venv/bin/uvicorn app.main:app --reload
```

Work in `backend/app`: routes in `api/v1/routes`, logic in `services`, Pydantic in
`schemas`, ORM in `models`. Schema changes get a new revision:

```bash
cd backend && .venv/bin/alembic revision -m "add alerts table"   # then edit the file
.venv/bin/alembic upgrade head
.venv/bin/alembic heads                                          # must print exactly one
```

Before pushing:

```bash
./deployment/scripts/run_tests.sh backend/tests
cd backend && PYTHONPATH=. .venv/bin/python ../database/schema/export_schema.py   # if models changed
git add backend database docs/api
git commit -m "feat: add alerts list and detail API"
git push -u origin feature/backend-alerts-api
```

Update `docs/api/api-contracts.md` in the same PR whenever a response shape changes.

### AI/ML and data — Yash

```bash
git checkout dev && git pull
git checkout -b feature/ml-<topic>                 # e.g. feature/ml-sequence-model
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt -r ai/requirements.txt pytest jsonschema pandas
```

Work in `ai/` (`datasets`, `feature_engineering`, `training`, `evaluation`, `inference`,
`ingestion`) and `tests/ml`. Raw archives stay untracked; only the small bundled demo
replay and checkpoint are committed, and both are justified in their folder READMEs.

If the feature contract changes:

```bash
# edit ai/inference/contract.py, bump CONTRACT_VERSION, then
backend/.venv/bin/python ai/feature_engineering/build_feature_schema_contract.py
# and mirror the change in backend/app/schemas/inference.py
```

Before pushing:

```bash
./deployment/scripts/run_tests.sh tests/ml backend/tests/test_inference_schemas.py
git add ai tests/ml docs/api docs/research
git commit -m "feat: add sequence-aware forecasting head"
git push -u origin feature/ml-sequence-model
```

The PR must include the metrics table (precision, recall, F1, ROC-AUC, PR-AUC, lead time)
and say which dataset split produced it. Never quote a single accuracy number.

### UI/UX, QA, and documentation — Kshitij

```bash
git checkout dev && git pull
git checkout -b docs/<topic>                       # or fix/<bug> for a bug you fixed
```

Wireframes and exports go in `docs/`, test scenarios in `tests/`, the user guide and demo
notes in `docs/demo/`. For a bug you found but cannot fix, open an issue with the *Bug
report* template and the `bug` label; add `urgent` if it blocks the demo. Before pushing:

```bash
./deployment/scripts/run_tests.sh                  # only if you touched code
git add docs tests
git commit -m "docs: add analyst user guide"
git push -u origin docs/user-guide
```

### DevOps, integration, and presentation — Arnav

```bash
git checkout dev && git pull
git checkout -b chore/<topic>                      # e.g. chore/compose-redis
cp .env.example .env
docker compose up --build                          # full stack: db, backend, frontend
```

Work in `deployment/`, the two compose files, the two Dockerfiles, and `.github/`. Before
pushing:

```bash
docker compose config --quiet                      # compose file validates
docker compose up --build -d && curl -s 127.0.0.1:8000/api/v1/health && docker compose down
./deployment/scripts/run_tests.sh
git add deployment docker-compose.yml docker-compose.live.yml backend/Dockerfile frontend/Dockerfile .github
git commit -m "chore: add redis service for background jobs"
git push -u origin chore/compose-redis
```

Run `./deployment/scripts/github_setup.sh` once (needs the GitHub CLI and admin rights)
to create the issue labels and protect `main` and `dev`.

### Team lead — Durgesh

Reviews and merges. To integrate `dev` into `main` after the end-to-end check:

```bash
git checkout dev && git pull
./deployment/scripts/run_tests.sh && (cd frontend && npm test && npm run build)
git checkout main && git pull
git merge --ff-only dev
git push origin main
```

If `--ff-only` refuses, someone pushed to `main` directly. Merge `main` into `dev` first,
then retry.

## Commit messages

Use a simple prefix and a short imperative summary:

`feat:` new feature · `fix:` bug fix · `docs:` documentation · `refactor:` cleanup ·
`test:` tests · `chore:` setup/config

Examples: `feat: add alert detail API`, `fix: handle missing packet timestamps`.

## Pull requests

Open PRs against `dev`. The template asks for what changed, screenshots for UI, test
status, and known limitations. At least one teammate reviews before merging. Keep PRs
small enough to review in ten minutes.

CI must be green: backend tests, ML contract tests, frontend build, and compose validation.

## Issues and labels

Track work in GitHub Issues and Projects with the columns
Backlog → This Week → In Progress → Blocked → Review → Ready for Integration → Done.

Labels: `frontend`, `backend`, `ml`, `bug`, `urgent`, `demo`, `docs`.

## Rules that keep the demo safe

- Never commit `.env`, raw datasets, large model binaries, or `node_modules`.
  `.gitignore` blocks them; check `git status` before committing. The only committed data
  artifacts are the small demo replay and checkpoint, each justified in its folder README.
- Never edit an Alembic migration that has reached a shared database. Add a new one, and
  confirm `alembic heads` prints exactly one head.
- Never change `docs/api/feature_schema_contract.json` by hand. Edit
  `ai/inference/contract.py`, regenerate it, bump the version, and update
  `backend/app/schemas/inference.py` in the same PR.
- Never install npm packages from the repository root. Run `npm install` inside
  `frontend/` so the dependency lands in `frontend/package.json` and reaches the Docker image.
- Never push directly to `main`.
- Every new API route, parser, feature calculator, or screen ships with a test.
- If you are blocked for more than half a day, move the card to *Blocked* and say so at
  standup: what you finished, what you are doing today, what is blocking you.

## Naming conventions

- Files: `lowercase_with_underscores` (Python) or `kebab-case` (docs); be consistent within a folder.
- API routes: `/api/v1/alerts`, `/api/v1/predictions`.
- Database tables and columns: `snake_case`.
- React components: `PascalCase`.

## Environment and secrets

- `.env.example` files show the shape only. Never commit a real `.env`.
- Share secrets privately; rotate demo secrets before any shared deployment.
- The backend refuses to start outside development with the default `JWT_SECRET_KEY` or
  one shorter than 32 characters.

## Tests

```bash
./deployment/scripts/run_tests.sh          # backend unit + HTTP tests, ML contract tests
cd frontend && npm test && npm run build   # type-check and production build
```

See [`tests/README.md`](tests/README.md) for what lives where.
