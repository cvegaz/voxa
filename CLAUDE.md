# CLAUDE.md — Voxa

Guide for agents working in this repo. (For the index of specs and modules, see `README.md`.)

## What Voxa is

An app for capturing data through **audio narration** and saving it to an **Excel file**, using OpenAI to transcribe and extract the fields. End-to-end flow:

```
Load Excel template → detect schema (columns/types) → confirm
   → record/upload audio → transcribe (Whisper) → accept text
   → extract fields (LLM) → append row (kept in the DB) → view result
   → finalize (or reach the trial allowance) → download the rebuilt .xlsx
```

OpenAI does **all** of the AI work: transcription (Whisper `whisper-1`) + context enrichment and field extraction (`gpt-4o-mini`).

The extraction/export flow is **stateless on disk**: each accepted row is persisted in Postgres (`extraction_records`, the single source of truth), the session auto-finalizes at the row cap or on demand, and the final `.xlsx` is **rebuilt in memory from the schema on download** (header + data only, no `Tipo_Dato`/`Ejemplo_Valor`). See [ADR-0013](docs/adr/0013-in-memory-rows-on-demand-excel-export.md).

The row cap is **3**, not the 5 of ADR-0013: ADR-0019 §2 lowered it to the anonymous
trial allowance and made it configurable (`ANONYMOUS_MAX_NARRATIONS`). There is one
constant for it, `MAX_ROWS_PER_SESSION` — see the demo-limits section below.

## Stack

- **Backend**: Python · FastAPI · `asyncpg` (PostgreSQL) · `openai` · `openpyxl`/`pandas` (Excel) · `uvicorn`.
- **Frontend**: React 18 · TypeScript · Vite · CSS Modules · Vitest.
- **Infra**: Docker Compose (Postgres 16 db, backend, frontend with Nginx). See `docker-compose.yml`.

## Commands

### With Docker (everything together, the simplest option)
```bash
docker compose up --build      # brings up db + backend + frontend
# frontend: http://localhost:5300   backend/docs: http://localhost:5310/docs
```
On startup, the backend applies migrations (`scripts/migrate.py`) before serving.

### Backend locally (without Docker)
```bash
cd backend
pip install -r requirements.txt
python scripts/migrate.py                       # applies migrations/*.sql
uvicorn app.main:app --reload --port 5310
pytest                                           # runs the full suite (testpaths=tests)
pytest tests/test_whisper_service.py            # a single file
```

### Frontend locally
```bash
cd frontend
npm install
npm run dev        # Vite on :5300 (strictPort), proxy /api → localhost:5310
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

## Public demo limits (ADR-0019) — read this before touching a cap

Voxa is exposed as an anonymous public demo, so **every OpenAI-spending path is
guarded**. The rules that must not be broken:

- **The recording cap is measured, never reported.** `AudioValidator` validates a
  duration produced by `AudioDurationProbe` (ffprobe on the uploaded bytes). The
  `duration` form field is telemetry only. Never wire a client-supplied number
  back into a control — that hole is what ADR-0019 exists to close, and
  `TestTranscribeEndpointTrustBoundary` is the regression suite for it.
- **The byte cap is not a duration control.** Size cannot bound seconds when the
  caller picks the bitrate (a 10-minute Opus file fits in 576 KB). It is a
  pre-filter so an absurd upload is never decoded.
- **Client IP behind a proxy is read from the right.** `TRUSTED_PROXY_HOPS`
  counts the proxies *we* run; the address sits at `parts[-hops]` of
  `X-Forwarded-For`. Reading `parts[0]` reads whatever the caller wrote.
- **Check budget before the OpenAI call, record after it succeeds.** A failed call
  costs nothing and must not consume budget.
- **The email soft gate grants nothing.** No quota, no token. An unverified
  address that unlocks anything is a Sybil hole.
- **Funnel writes are best-effort and wrapped.** Telemetry must never fail a
  request the user paid for. The `try/except` around each one is the design.
- **Every limit is an environment variable** (`app/constants.py`,
  `app/rate_limit.py`), documented inline in `backend/.env.example`. Invalid
  values raise at import **on purpose** — a cost control that silently falls back
  to a default is the failure being prevented.
- **`ffmpeg` is a hard runtime dependency** of the backend image. The test suite
  must keep running without it (the probe is injected).

Monthly report: `cd backend && .venv/bin/python scripts/funnel_report.py`.

## Secrets and configuration

- Variables in `backend/.env` (copied from `backend/.env.example`). **`.env` is in `.gitignore` and is NEVER committed.**
- `OPENAI_API_KEY` = real cost per use. Do not hardcode it in code, tests, `docker-compose.yml`, or screenshots.
- Inside Docker, `DATABASE_URL` points to the host `db` (the service name), not `localhost`; `docker-compose.yml` overrides it on top of the `.env`.
- The `postgres/postgres` credentials and the compose password are **for local development only**.

## Notes

- Architecture decisions and their rationale are recorded as ADRs in `docs/adr/` (start at `docs/adr/README.md`). When making a non-trivial design decision, add a new ADR.
- **Multi-language (ES/EN).** The UI is bilingual via a small in-house i18n layer (`frontend/src/i18n/`, ADR-0016). A record's language is **per-session, fixed when the template is confirmed** (`template_sessions.language`); transcription, prompts (`prompt_builder`, `llm_enrichment_service`), the enriched context, and date formatting (`date_normalizer`) all read it — ES → `17-sep-2026`, EN → `09/17/2026` (ADR-0017). Keep the per-language prompt templates and the month tables in sync when touching these.
- Detailed design specs are in `.kiro/specs/` (three modules: excel-template-loader, audio-transcription-controls, llm-extraction-excel-output).
- Pending items and the publishing/deployment roadmap are in `todo.md`.
- The folder's historical name was `my-data-app`; some old references may remain (e.g., comments in `docker-compose.yml`).
