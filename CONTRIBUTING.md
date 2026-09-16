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

| Member | Name | Owns |
| --- | --- | --- | --- |
| 1 | Adarsh | Frontend development + team lead + PPT storyline/narrative |
| 2 | Shreya | Backend development (APIs, auth, DB) + built the AI/LSTM forecasting model |
| 3 | Yash Bhanushali | AI model support + research work |
| 4 | Arnav | PPT design + documentation |
| 5 | Kshitij | Testing (backend + model validation) |
| 6 | Durgesh | AI model refinement — training improvements, tuning |


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
