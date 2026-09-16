# database/

PostgreSQL is the system of record. Nothing in this folder is applied automatically; the
backend owns every schema change.

## Where each artifact lives

| What | Where | Why there |
| --- | --- | --- |
| Schema design (ERD, tables, indexes) | `docs/architecture/database-schema.md` | Documentation |
| SQLAlchemy models | `backend/app/models/` | The backend owns the ORM |
| Alembic migrations | `backend/alembic/versions/` | Migrations import the backend models |
| Seed script (demo users) | `backend/scripts/seed_demo_users.py` | Uses the backend session and password hashing |
| Readable DDL snapshot | `schema/schema.sql` (this folder) | Lets reviewers read the schema without running Alembic |

## schema/

`schema.sql` is generated from the SQLAlchemy models, not from a live database, so it runs
anywhere. Regenerate it after any model change and commit the result:

```bash
cd backend && PYTHONPATH=. .venv/bin/python ../database/schema/export_schema.py
```

## Migration rules

1. Never edit a revision after it has reached a shared database. Add a new one.
2. Every schema change is one new revision, reviewed together with its model change.
3. Run `alembic upgrade head` after pulling database changes.
4. Keep the chain linear. Before pushing a new revision, confirm `alembic heads` reports
   exactly one head; two heads mean two people branched from the same parent.

Walkthrough: `docs/devlog/day-2-database-setup.md`.

## Seeding demo data

```bash
docker compose exec backend python scripts/seed_demo_users.py   # Docker
cd backend && PYTHONPATH=. .venv/bin/python scripts/seed_demo_users.py   # local venv
```

The built-in demo passwords are accepted only while `ENVIRONMENT=development`. Anywhere
else the script requires `DEMO_ADMIN_PASSWORD`, `DEMO_ANALYST_PASSWORD`, and
`DEMO_VIEWER_PASSWORD`.
