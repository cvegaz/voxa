# Voxa

> Turn spoken narration into structured spreadsheet data. Talk, and Voxa fills in
> your Excel file.

**Voxa** lets you capture data by **voice**: you upload an Excel template, narrate
the information out loud, and an LLM transcribes your speech and extracts the right
values into the right columns — appending a new row to your spreadsheet. No typing,
no forms.

<!-- TODO: add a short demo GIF/video of the real flow here — it sells the project more than anything else. -->
> _Demo GIF coming soon._

## How it works

```
Upload Excel template → detect schema (columns / types) → confirm
   → record / upload audio → transcribe (Whisper) → accept text
   → extract fields (LLM) → append row to the Excel file → see the result
```

OpenAI powers all of the AI: transcription with **Whisper** (`whisper-1`), plus
context enrichment and field extraction with **`gpt-4o-mini`**.

## Tech stack

| Layer | Technologies |
|-------|--------------|
| **Frontend** | React 18 · TypeScript · Vite · CSS Modules · Vitest |
| **Backend** | Python · FastAPI · `asyncpg` · `openai` · `openpyxl` / `pandas` · `uvicorn` |
| **Database** | PostgreSQL 16 |
| **AI** | OpenAI Whisper (`whisper-1`) + `gpt-4o-mini` |
| **Infra** | Docker Compose · Nginx (serves the frontend and proxies `/api`) |

## Architecture

```mermaid
flowchart LR
    U[User] --> FE[React SPA<br/>served by Nginx]
    FE -->|/api proxy| BE[FastAPI backend]
    BE --> OAI[OpenAI<br/>Whisper + gpt-4o-mini]
    BE --> DB[(PostgreSQL)]
    BE --> XLSX[.xlsx file on disk]
```

The backend follows a strict layered design (`routes` → `services` →
`repositories` → `models`). The browser only ever calls relative `/api/...` paths,
which Nginx (prod) or the Vite dev server (dev) proxy to the backend. See the
[Architecture Decision Records](Docs/adr/README.md) for the reasoning behind these
choices.

## Quick start (Docker)

The whole system — database, backend, and frontend — comes up with one command:

```bash
# 1. Provide your OpenAI key (see Configuration below)
cp backend/.env.example backend/.env   # then edit backend/.env

# 2. Build and run everything
docker compose up --build
```

- Frontend: <http://localhost:8080>
- Backend API docs (Swagger): <http://localhost:8000/docs>

On startup the backend applies database migrations (`scripts/migrate.py`) before
serving.

## Local development (without Docker)

**Backend**

```bash
cd backend
pip install -r requirements.txt
python scripts/migrate.py                # apply migrations/*.sql
uvicorn app.main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend
npm install
npm run dev        # Vite on :5173, proxies /api → localhost:8000
```

## Configuration

Backend configuration lives in `backend/.env` (copied from
`backend/.env.example`). It is git-ignored and must never be committed.

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | `postgresql://user:password@host:port/database` |
| `OPENAI_API_KEY` | OpenAI key — used for both transcription and extraction. **Every call costs real money**, so set a monthly spending cap in the OpenAI dashboard. |

Inside Docker Compose, `DATABASE_URL` is overridden to point at the `db` service.

## Tests

```bash
cd backend  && pytest        # backend suite (pytest + hypothesis)
cd frontend && npm test      # frontend suite (vitest)
```

Voxa is developed test-first: each service and endpoint has a corresponding test
(see [ADR-0009](Docs/adr/0009-test-driven-development.md)).

## Project structure

The product is organized into three independent modules, each with its own
requirements, design, and tasks spec under `.kiro/specs/`:

| Module | Description |
|--------|-------------|
| **excel-template-loader** | Loading and validation of the Excel template file, schema detection (columns, data types, examples), and confirmation screen |
| **audio-transcription-controls** | Audio recording from the microphone, transcription to text, and Accept / Add new controls |
| **llm-extraction-excel-output** | Field extraction with an LLM, record insertion into the Excel file, and real-time view |

Module data flow:

```
excel-template-loader
        ↓  Confirmed Esquema_Columnas
audio-transcription-controls
        ↓  Accepted Texto_Transcrito
llm-extraction-excel-output
        ↓  Record inserted into Archivo_Excel
```

## Documentation

- **Architecture decisions**: [`Docs/adr/`](Docs/adr/README.md) — the *why* behind the design.
- **Module specs**: `.kiro/specs/` (requirements, design, tasks per module).
- **Contributor guide**: [`CLAUDE.md`](CLAUDE.md) — conventions and commands.
- **Roadmap**: [`todo.md`](todo.md) — planned features and the publishing/deployment plan.

## License

Not yet licensed (MIT planned). Until a `LICENSE` file is added, all rights are reserved.
