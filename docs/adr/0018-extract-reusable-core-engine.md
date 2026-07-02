# 0018. Extract a reusable narration→structured-data core (`voxa-core`)

- **Date**: 2026-07-01
- **Status**: Accepted

## Context

Voxa is a working product: it turns spoken narration into structured spreadsheet
data (audio → Whisper → LLM extraction → row → on-demand `.xlsx`), with a layered
backend (ADR-0004), a test-first suite (ADR-0009), and end-to-end ES/EN support
(ADR-0016, ADR-0017).

A paying client needs **playPro Stats**: an American-football (FBA — *fútbol
americano*, kept distinct from soccer) play-by-play variant that captures game
stats by voice. Two earlier prototypes exist (a Groq/CSV
"laboratory" and a FastAPI/Postgres scaffold); they are kept only as a source of
**domain knowledge** — the ~45-field play schema, the extraction prompts, the
"carry the previous play forward" rules, and a normalized league/team/player/game
database design — not as code to reuse.

playPro shares Voxa's spine (transcribe → LLM-extract → persist → export) but
diverges on substance:

- It is **sequential**: each play depends on the previous one (down progression,
  quarterback carry-forward, running score, field position). Voxa today treats
  every narration as an **independent** flat row.
- It is **reference-grounded**: player numbers and team names must be confirmed
  against a registered roster. Voxa has no notion of a controlled vocabulary.
- It produces **hundreds of rows per game** and is **database-first**, whereas
  Voxa caps a session at five rows and is stateless on disk (ADR-0013).

Two further forces:

- More bespoke variants are anticipated — the expected pattern is "someone sees
  Voxa and asks for a similar app for their domain."
- Voxa must remain a **standalone flagship/portfolio repository** scoped to
  "audio → structured Excel," while client code is **commercial and private**.

Putting both products in one repository would either bloat Voxa with
football-specific logic or force a fork whose divergence grows and into which core
fixes never propagate.

## Decision

We will extract Voxa's **domain-agnostic extraction engine** into a separate,
installable package — **`voxa-core`** — consumed by both Voxa and each per-client
product (starting with playPro Stats) as a thin **configuration + domain layer** on
top. This is a shared core, **not a fork**.

**The boundary.** The core owns *how* we get from audio to validated structured
records given a schema and a prompt strategy. Each product owns *what* the schema
is, *what* the prompt says, *which* policies apply, and *how* results are persisted
and surfaced.

| Module (in `backend/app/services` today) | Destination | Rationale |
|---|---|---|
| `whisper_service` | **core** | Transcription; already language-parameterized |
| `llm_extraction_service` | **core** | Generic LLM call + retry/backoff |
| `llm_enrichment_service` | **core** | Generic context enrichment (prompt text is a hook) |
| `response_parser` | **core** | JSON → schema mapping + value normalization |
| `date_normalizer` | **core** | Locale-aware date utility |
| `excel_exporter` | **core** | Schema + records → `.xlsx` in memory |
| `schema_extractor` | **core** | `.xlsx` header rows → `ColumnSchema` (utility) |
| `audio_validator` | **core** | Format/duration checks, already configurable |
| `exceptions` + base models (`ColumnSchema`, `ColumnDef`, `ValidationResult`, `RecordValue`, `ExtractionResult`) | **core** | Shared error taxonomy and data contracts |
| Cross-cutting patterns (injectable OpenAI client; retry + error-translation) | **core** | The reusable engineering asset |
| `prompt_builder` | **core interface / product implementation** | Assembling a prompt is generic; the instructions/examples are domain |
| `extraction_orchestrator` | **core interface / product policy** | The pipeline is generic; row cap and stateful-vs-independent behavior are product choices |
| `repositories/*` | **core interface / product schema** | The data-access pattern is generic; the concrete tables are per product |
| `excel_validator` | **Voxa product** | Encodes Voxa's template-upload rules (≤8 cols, `Tipo_Dato`/`Ejemplo_Valor`) |
| `dataframe_converter` | **Voxa product** | Reads uploaded-template data rows |
| `context_validator`, `acceptance_validator` | **Voxa product** | Tied to Voxa's template/transcription session flow |
| `contact_routes`, landing, frontend | **Voxa product** | Marketing/UI, out of the engine |
| 5-row cap, on-demand export, stateless-on-disk | **Voxa product policy** | ADR-0013 decisions, not engine invariants |

**Staged extraction, not a big-bang.** We move the stable, high-reuse modules
first; we define **interfaces** (protocols) in core for the three pluggable seams
(`PromptBuilder`, orchestrator policy, repositories) and keep Voxa's current
concrete versions as its product implementation. We promote a module from product
to core only when a **second real use** (playPro) proves the abstraction — we
generalize on evidence, not on speculation.

**Consumption model.** During the unstable phase, both products depend on
`voxa-core` via an **editable/path install** (`pip install -e ../voxa-core`), so a
change to the engine is picked up immediately by Voxa and playPro with no version
ceremony. Once the engine stabilizes, we switch to **pinned semantic versions**
(`voxa-core==0.1.x`) so each product upgrades deliberately.

**Repository layout.** Three sibling repositories:

- `voxa` — the standalone product and portfolio piece (audio → Excel), depends on
  `voxa-core`. Public.
- `voxa-core` — the engine. Private for now.
- `playpro_stats` — the client product, depends on `voxa-core`. Private. It carries
  its **own** ADR log, README, and test suite, referencing this ADR as its origin.

## Consequences

- **Positive**: one source of truth for the engine — a fix or a hardening done for
  the paying client benefits Voxa (and every future client) automatically. Voxa
  stays clean and small as a portfolio artifact. New bespoke clients become
  "new repo + config + domain layer on the same core" instead of new forks. The
  boundary makes "sport-specific = configuration, general = shared code" an
  enforceable rule rather than a good intention.
- **Negative / trade-offs**: extraction is real refactoring work and adds a package
  seam (imports, packaging, versioning) that a single repo does not have. Defining
  the three interfaces up front costs design time. Until versions are pinned, an
  engine change can break a consumer silently — the editable install trades safety
  for iteration speed, and we accept that during the unstable phase.
- **Neutral**: the boundary is a convention enforced by review and by the package
  import graph, not by tooling. The exact contents of `voxa-core` will shift as
  playPro reveals which abstractions are real; this ADR fixes the *direction* and
  the *first cut*, not the final line.

## Alternatives considered

- **Fork Voxa into playPro** — rejected: the products diverge on substance, so the
  fork drifts; core fixes never flow back; and it entangles commercial client code
  with the public portfolio repo's history and visibility.
- **Monorepo** (core + both apps in one repository) — viable and lower-friction for
  versioning, but it conflicts with the requirement that Voxa be its own
  standalone public repository; kept as the fallback if cross-repo version pinning
  becomes painful for a solo maintainer.
- **Copy-paste the good parts into playPro, no shared package** — rejected: the
  well-tested engine (retry/error-translation, response parsing, export) would
  immediately begin to diverge, defeating the reason to reuse it.
- **Config-only multi-tenant Voxa** (one deployment, per-client config rows) —
  rejected for now: it would drag football's stateful/roster/DB-first model into
  the generic product and couple client delivery to Voxa's release cycle.
