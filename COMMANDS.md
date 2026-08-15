# Commands

Quick reference for running Voxa with Docker.

> Run all commands from the project root, where `docker-compose.yml` lives.

## Start the app

| Goal | Command |
|------|---------|
| Start everything (normal use) | `docker compose up -d` |
| Start and rebuild (after code changes) | `docker compose up -d --build` |
| Check running containers | `docker compose ps` |
| Follow live logs (e.g. backend) | `docker compose logs -f backend` |

Then open 👉 **http://localhost:5300**

## Stop the app

| Goal | Command |
|------|---------|
| Stop everything (keeps the database) | `docker compose down` |
| Stop **and wipe the database** (start fresh) | `docker compose down -v` |
| Pause without removing | `docker compose stop` |
| Resume what was paused | `docker compose start` |

## Notes

- **`-d`** = *detached*: runs in the background and returns the terminal to you.
- **`down`** removes containers and the network, **but not the data** (it stays in the volumes). Bring it back with `docker compose up -d`.
- **`down -v`** also deletes the data (the database resets and re-runs migrations on the next start). Use it only when you want a clean slate.

### Daily workflow, in two lines

```bash
docker compose up -d      # start working
docker compose down       # stop working
```

## Fresh start from scratch (after code fixes)

Use this when you want to test the app from zero: an empty database and images
rebuilt with your latest code changes.

```bash
docker compose down -v          # stop and wipe the database (volumes)
docker compose up -d --build    # rebuild images and start fresh
```

What happens:

- `down -v` deletes the data volumes, so the database starts empty.
- `up -d --build` rebuilds the backend/frontend images with your code changes;
  the migrations re-run automatically on the empty database.
- The app comes up at the first step of the flow, with no active session.

> Tip: if the browser tab was already open, do a hard reload (Ctrl+F5) so it
> does not serve cached files from the previous version.

## Service URLs

Voxa owns the **`53xx` block** in this machine's port registry
(`~/Dev/PORTS.md`). Roles by offset: `+00` frontend, `+01` landing, `+10`
backend, `+30` database. Never take a port outside the block — 5433/8080/5173
belong to other projects, and Vite runs with `strictPort: true` so a collision
fails loudly instead of hopping to the next free port.

| Service | URL |
|---------|-----|
| Frontend (Nginx, Docker) | http://localhost:5300 |
| Frontend (Vite dev) | http://localhost:5300 |
| Landing (Vite dev) | http://localhost:5301 |
| Backend API docs (Swagger) | http://localhost:5310/docs |
| PostgreSQL (DB client) | `localhost:5330` |

## Quality checks

The same three that CI runs. Running them locally before pushing is the whole
point of having them.

```bash
cd backend  && .venv/bin/python -m pytest -q     # 506 tests, no DB and no API key needed
cd frontend && npm run lint && npx tsc -b --noEmit && npm test
cd landing  && npm run lint && npx tsc -b --noEmit && npm test
```

The backend suite runs on an **empty environment** on purpose — CI provides no
secrets, and `tests/test_offline_suite.py` asserts that guarantee. If a test ever
starts needing a key, it fails there rather than in a red build weeks later.

## Public demo report

Sessions, "aha" rate, downloads, leads, walls hit, spend, and cost per captured
lead (ADR-0019 §7):

```bash
cd backend && .venv/bin/python scripts/funnel_report.py            # this month
cd backend && .venv/bin/python scripts/funnel_report.py 2026-08-01 # from a date
```

## Dependencies

`backend/requirements.txt` is **generated** — never edit it by hand. Change
`requirements.in` (or `requirements-dev.in`) and regenerate both:

```bash
cd backend
.venv/bin/pip-compile --strip-extras requirements.in
.venv/bin/pip-compile --strip-extras requirements-dev.in
```
