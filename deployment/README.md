# deployment/

Everything needed to run the stack on one machine. The Dockerfiles live next to the code
they build so each build context stays small.

## Service images

| Service | Image or Dockerfile | Base | Notes |
| --- | --- | --- | --- |
| `db` | `postgres:16-alpine` | — | Data persisted in the `postgres_data` volume |
| `backend` | `backend/Dockerfile` | `python:3.12-slim` | Built from the repository root so the image also contains `ai/`; runs `alembic upgrade head` then uvicorn |
| `frontend` | `frontend/Dockerfile` | `node:20-alpine` | Multi-stage build, served as a Next.js standalone bundle |

## Compose files

| File | Purpose |
| --- | --- |
| `docker-compose.yml` (repository root) | The default stack: `db`, `backend`, `frontend` |
| `docker-compose.live.yml` (repository root) | Adds the authorised Zeek live-ingestion bridge |

## One-command demo stack

```bash
cp .env.example .env          # set JWT_SECRET_KEY
docker compose up --build
```

Frontend on `http://127.0.0.1:3000`, backend on `http://127.0.0.1:8000`, PostgreSQL on
`5432`. `docker compose down` keeps the database volume; `docker compose down -v` deletes it.

## scripts/

| Script | What it does |
| --- | --- |
| `bootstrap_backend.sh` | Creates the backend virtualenv, installs dependencies, runs migrations, seeds demo users |
| `run_tests.sh` | Runs the Python suites from the repository root; forwards any pytest arguments |
| `start_live_demo.sh` | Brings up the stack plus the Zeek bridge for an authorised local-network demo |
| `github_setup.sh` | One-time repository setup: issue labels and branch protection (needs the GitHub CLI with admin rights) |
