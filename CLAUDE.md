# CLAUDE.md — Voxa

Guide for agents working in this repo. (For the index of specs and modules, see `README.md`.)

## What Voxa is

An app for capturing data through **audio narration** and saving it to an **Excel file**, using OpenAI to transcribe and extract the fields. End-to-end flow:

```
Load Excel template → detect schema (columns/types) → confirm
   → record/upload audio → transcribe (Whisper) → accept text
   → extract fields (LLM) → insert row into the Excel file → view result
```

OpenAI does **all** of the AI work: transcription (Whisper `whisper-1`) + context enrichment and field extraction (`gpt-4o-mini`).

## Stack

- **Backend**: Python · FastAPI · `asyncpg` (PostgreSQL) · `openai` · `openpyxl`/`pandas` (Excel) · `uvicorn`.
- **Frontend**: React 18 · TypeScript · Vite · CSS Modules · Vitest.
- **Infra**: Docker Compose (Postgres 16 db, backend, frontend with Nginx). See `docker-compose.yml`.

## Commands

### With Docker (everything together, the simplest option)
```bash
docker compose up --build      # brings up db + backend + frontend
# frontend: http://localhost:8080   backend/docs: http://localhost:8000/docs
```
On startup, the backend applies migrations (`scripts/migrate.py`) before serving.

### Backend locally (without Docker)
```bash
cd backend
pip install -r requirements.txt
python scripts/migrate.py                       # applies migrations/*.sql
uvicorn app.main:app --reload --port 8000
pytest                                           # runs the full suite (testpaths=tests)
pytest tests/test_whisper_service.py            # a single file
```

### Frontend locally
```bash
cd frontend
npm install
npm run dev        # Vite on :5173, proxy /api → localhost:8000
npm test           # vitest run
npm run build      # tsc -b && vite build
npm run lint       # eslint
```

## Backend architecture (by layers)

`backend/app/` follows a strict separation. When adding features, respect the layers:

- **`routes/`** — FastAPI endpoints. Prefixes: `/api/templates`, `/api/transcriptions`, `/api/extraction`. They only orchestrate; no heavy logic here.
- **`services/`** — business logic. All of the domain lives here (whisper, LLM extraction/enrichment, validators, excel_writer, orchestrator, prompt_builder, response_parser…).
- **`repositories/`** — data access (Postgres via `asyncpg`).
- **`models/`** — Pydantic models / data schemas.
- **`migrations/`** — versioned SQL (`00N_*.sql` + its `_rollback.sql`). Applied with `scripts/migrate.py`.

The OpenAI services (`whisper_service`, `llm_extraction_service`, `llm_enrichment_service`) take an optional `AsyncOpenAI` client in the constructor; if it is `None`, they create one with `OPENAI_API_KEY`. **Keep this pattern** — it is what allows injecting a mock in the tests.

## Conventions that must NOT be broken

- **camelCase API contract.** The frontend and backend speak camelCase. Errors are ALWAYS flattened to `{ "detail": str, "errorCode": str }` (see the exception handlers in `app/main.py`). Do not return a nested `detail` or snake_case to the client.
- **The `/api` proxy.** The frontend calls relative `/api/...` routes (never absolute URLs to the backend). This is resolved by the Vite proxy in dev (`vite.config.ts`) and Nginx in prod (`frontend/nginx.conf`). See the comment about `proxy_pass` without a trailing `/`.
- **TDD / tests first.** There is a broad suite (pytest + hypothesis in the backend, vitest in the frontend). Every service and endpoint has its test. When touching logic, update or add the corresponding test; do not leave functionality uncovered.
- **OpenAI errors** are translated into domain exceptions (`exceptions.py`: `LLMUnavailableError`, `LLMInvalidResponseError`, etc.) with retries for transient errors (connection/timeout/5xx). Follow that pattern when adding LLM calls.

## Secrets and configuration

- Variables in `backend/.env` (copied from `backend/.env.example`). **`.env` is in `.gitignore` and is NEVER committed.**
- `OPENAI_API_KEY` = real cost per use. Do not hardcode it in code, tests, `docker-compose.yml`, or screenshots.
- Inside Docker, `DATABASE_URL` points to the host `db` (the service name), not `localhost`; `docker-compose.yml` overrides it on top of the `.env`.
- The `postgres/postgres` credentials and the compose password are **for local development only**.

## Notes

- Architecture decisions and their rationale are recorded as ADRs in `Docs/adr/` (start at `Docs/adr/README.md`). When making a non-trivial design decision, add a new ADR.
- Detailed design specs are in `.kiro/specs/` (three modules: excel-template-loader, audio-transcription-controls, llm-extraction-excel-output).
- Pending items and the publishing/deployment roadmap are in `todo.md`.
- The folder's historical name was `my-data-app`; some old references may remain (e.g., comments in `docker-compose.yml`).
