# TODO — Improvements for future versions

## Pending discussion and implementation

### 1. Record confirmation before saving
- Show the user the fields extracted by the LLM before inserting them into the Excel file
- Allow editing individual values before confirming the insertion
- Decide whether this is a mandatory step or a configurable option

### 2. Narration language
- Define whether the app will support only Spanish or multiple languages
- Affects the Transcriptor configuration and the LLM prompts
- Consider language selection at load time or automatic detection

### 3. Multiple records in a single audio recording
- Allow a single narration to generate more than one row in the Excel file
- Example: "Juan is 30 years old; Maria is 25"
- Decide whether the LLM automatically detects multiple records or whether it is always 1 recording = 1 row

### 4. Persistence of the Contexto_Enriquecido
- Save the Contexto_Enriquecido associated with the Excel file so it is not lost when the app closes
- Options: store it as metadata in the same .xlsx, as an attached .json file, or in the app's local storage
- Evaluate whether, on reopening, it is reused without asking the user for the description again

### 5. Dockerize the entire application
- Create a docker-compose setup with services: Python backend, React frontend, PostgreSQL
- Make deployment easy on any machine without manual configuration
- Include volumes for persisting data and Excel files

### 6. Replace OpenAI with a local model (Ollama)
- Allow using a local LLM (LLaMA/Mistral via Ollama) instead of the OpenAI API
- Remove the dependency on an external API and its associated costs
- Evaluate extraction quality with local models vs. OpenAI

### 7. Bilingual frontend (Spanish + English) — ✅ mostly done (2026-06-29, ADR-0016)
- [x] User-facing frontend available in both Spanish and English
- [x] i18n layer so all UI strings, button labels, and error messages switch between languages
- [x] Language selector (top-right ES/EN switcher, default Spanish, persisted in localStorage)
- [x] The selected language sets the expected transcription input language (Whisper)
- [ ] Optional: auto-detect the browser language on first visit
- [ ] Remaining LLM-side language work (prompts, date format) lives in #8

### 8. Multi-language infrastructure for end-to-end records (any language)
> Goal: when we want to run the app in any language, the infrastructure and code must automatically accept and process the record in each language end-to-end — not just translate the UI (#7). Today most of the pipeline is hardcoded to Spanish.
- **Per-session language**: store the chosen/detected language on the session (DB column + migration) so transcription, extraction, and output all stay consistent for that record.
- **Transcription**: ✅ done — `whisper_service.transcribe()` takes a `language` arg (the UI sends es/en per request); the old hardcoded `LANGUAGE = "es"` is gone. Still pending: persist it per session rather than per request.
- **LLM prompts**: make the extraction/enrichment prompts (`prompt_builder.py`, `llm_enrichment_service.py`, currently Spanish) language-aware via templates per language, so the model is instructed in/for the right language.
- **Schema data-type names**: the Excel template type values (`texto`, `número entero`, `fecha DD/MM/YYYY`, `booleano`) are Spanish words — schema detection and type parsing must recognize the equivalents in each supported language (or normalize to a language-agnostic internal enum).
- **Locale-aware value parsing/formatting** when writing to the Excel file:
  - Dates: `DD/MM/YYYY` vs `MM/DD/YYYY` and other locale orders.
  - Numbers: decimal/thousands separators (`1.000,50` vs `1,000.50`).
  - Booleans: localized truthy/falsy words (`sí/no`, `yes/no`, `true/false`, etc.).
- **Enriched context language**: keep `Contexto_Enriquecido` in the record's language so later extractions match.
- **Error messages from the pipeline**: LLM/transcription/validation errors surfaced to the user should be localized (ties into #7).
- **Tests**: add fixtures and cases per language (at least ES + EN) for transcription, extraction, parsing, and Excel output.
- **Docs**: document the list of supported languages and how the language is selected/detected.

### 9. Tier-based recording limit
- The max audio recording length is currently **20s** (free tier), enforced both
  client-side (auto-stop in `AudioRecorder`) and server-side (`AudioValidator`).
- The limit is already configurable (a `maxDurationSeconds` prop on the recorder
  and a `max_duration_seconds` constructor arg on the validator, both defaulting
  to `MAX_AUDIO_DURATION_SECONDS` in `app/constants.py`).
- For a paid tier: source the cap from the user's plan and pass it through both
  layers, instead of using the single free-tier default.

---

# Publishing and deployment roadmap

> Three independent phases. You can do Phase A and B without C.
> Golden rule: the public repo showcases your CODE; the deployment exposes the SERVICE.
> Every user who uses the service spends YOUR OpenAI balance → do not open it to the internet without the Phase C protections.

## Phase A — Push the repo to GitHub (private or public)

### A.1 Secrets hygiene (CRITICAL before the first push)
- [ ] Confirm that `backend/.env` is NOT tracked: `git ls-files | grep .env` should return nothing (already verified ✅)
- [ ] Check that there are no hardcoded keys in code, tests, `docker-compose.yml`, README, or screenshots
- [ ] Confirm that `backend/.env.example` exists and contains the variables WITHOUT real values (only `OPENAI_API_KEY=`)
- [ ] Set a monthly spending limit in the OpenAI dashboard (Billing → usage limits) as a safety net

### A.2 Base repo files
- [ ] Add a `LICENSE` (MIT recommended for a portfolio) — it currently does NOT exist
- [ ] Review/complete `.gitignore` (env, `node_modules`, `__pycache__`, generated `*.xlsx`, `.venv`)
- [ ] Minimal `README.md`: what it does, stack, how to run it (`docker compose up --build`)

### A.3 First push
- [ ] Create the repo on GitHub (start PRIVATE if you do not want exposure yet)
- [ ] Verify the history: `git log` must not contain any commit with the key (if it ever did, you need to clean the history with git-filter-repo or BFG and ROTATE the key)
- [ ] `git push` and check on the GitHub website that nothing sensitive was uploaded

## Phase B — Make it public as a "flagship" portfolio piece

### B.1 A README that sells the project (what a recruiter looks at most)
- [ ] Title + one clear sentence about what Voxa solves (audio → structured data in Excel)
- [ ] **Demo as a GIF or short video** of the real flow working (this counts for more than having the app deployed)
- [ ] Stack section (React/Vite, FastAPI, PostgreSQL, OpenAI Whisper + LLM, Docker)
- [ ] Architecture diagram: Frontend → Nginx (proxy `/api`) → Backend → OpenAI / Postgres
- [ ] One-command startup instructions (`docker compose up --build`) + how to set up the `.env`
- [ ] Mention the test suite and how to run it (`pytest`, `npm test`)

### B.2 Visible repo quality
- [ ] Optional badges (build/tests, license)
- [ ] Clean folder structure and a `CONTRIBUTING` file or note on how it is organized
- [ ] Close/tag the TODOs already done (e.g., item 5 "Dockerize" — ALREADY done)

### B.3 Make it public
- [ ] Change the repo visibility to public in GitHub Settings
- [ ] Add it to your profile/portfolio with a link to the demo

## Phase C — Security for deployment and production

> Do ALL of this BEFORE exposing the app to the internet anonymously.

### C.1 Secrets and configuration (not in the repo)
- [ ] `OPENAI_API_KEY` and credentials are injected from the hosting provider's secrets manager (Railway/Render/Fly/AWS Secrets), NOT from a versioned `.env`
- [ ] Change `POSTGRES_PASSWORD: postgres` (docker-compose.yml:24) to a strong password sourced from secrets
- [ ] Production `DATABASE_URL` separate from the dev one

### C.2 Cost and abuse control (because you pay for every call)
- [ ] Rate limiting in the backend (requests per IP/user per minute) — e.g., slowapi for FastAPI
- [ ] Size and duration limits for accepted audio in `transcription_routes.py`
- [ ] Authentication / login (even a basic one) so that the service is NOT anonymous and open
- [ ] Keep the monthly OpenAI spending cap active

### C.3 Network exposure
- [ ] HTTPS required (most hosts provide it for free with a domain)
- [ ] Do NOT expose Postgres (5433) or the backend (8000) directly to the internet; only the frontend/proxy is public
- [ ] CORS locked down to the real frontend origins
- [ ] Review security headers and disable the public Swagger `/docs` if you do not want it

### C.4 Privacy (the app processes voice = personal data)
- [ ] Privacy notice: what is done with the audio, that it is sent to OpenAI, whether or not it is stored
- [ ] Decide and document whether the audio is deleted after processing or persisted
- [ ] Review what is stored in the `excel_data` volume and for how long

### C.5 Operations
- [ ] Basic logging and error monitoring
- [ ] Database backups
- [ ] Healthchecks and a restart policy in the deployment
