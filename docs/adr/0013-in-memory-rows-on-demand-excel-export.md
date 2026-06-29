# 0013. In-memory working rows with on-demand Excel export

- **Date**: 2026-06-26
- **Status**: Accepted

## Context

The original extraction design (in `.kiro/specs/llm-extraction-excel-output/`)
materializes the `.xlsx` **on the server's disk after every accepted row**: it
loads the workbook from `template_sessions.file_path`, clears data rows, rewrites
all rows, and saves back to disk. This shaped three problems that surfaced in
practice:

1. **The flow never produces `file_path`.** The upload route reads the workbook
   into memory but never writes it to disk nor stores a path, so `file_path` is
   always `NULL`. At extraction time `ExcelWriter.write(df, None, schema)` calls
   `load_workbook(None)` and raises `TypeError: expected str, bytes or
   os.PathLike object, not NoneType`, which the route flattens to a generic
   `DATABASE_ERROR` / "Error interno del servidor". Extraction is fully broken.
2. **Container disk is the wrong home for the artifact.** The backend runs in a
   container with ephemeral local disk and no volume mounted for uploads. Even if
   `file_path` were set, a restart or redeploy would lose the files, and there is
   **no download endpoint** — the user has no way to retrieve a file that only
   exists on the server.
3. **Duplicated state.** The same rows live in both `extraction_records` (one row
   per record, the source the UI reads) and `template_sessions.dataframe_json` (a
   pandas `DataFrame` re-serialized on every extraction). Two sources of truth
   that can diverge, plus an O(n) full-file rewrite per row.

The product is a short capture session: the user narrates a handful of rows and
wants the resulting spreadsheet. There is no requirement to keep editing a
long-lived file on the server, and the captured target template carries no
formatting worth preserving beyond its column names.

## Decision

We will treat the **accumulated rows as in-memory/database working state and
materialize the `.xlsx` only on demand**, never persisting a spreadsheet file to
disk.

- **Single source of truth.** `extraction_records` (rows keyed by session) is the
  working structure. We stop maintaining `template_sessions.dataframe_json` as a
  parallel copy and stop writing any `.xlsx` to disk per row. `ExcelWriter`'s
  per-row disk write is removed from the extraction path.
- **On-demand export, reconstructed from the schema.** A new export service builds
  a fresh workbook **in memory** (`openpyxl` → `BytesIO`) from the
  `ColumnSchema` + the session's records: one header row of column names followed
  by the data rows. We do **not** reproduce the uploaded template's formatting,
  titles, or header rows 1–3 — in particular the `Tipo_Dato` (row 2) and
  `Ejemplo_Valor` (row 3) scaffolding rows are schema metadata only and never
  appear in the final file (see Alternatives, option A). The file is served via
  a download endpoint as a `StreamingResponse` with a
  `Content-Disposition: attachment` filename.
- **Session closes on "Finalize" OR 5 rows, whichever comes first.** A "Finalizar"
  action is always available; reaching 5 records also closes the session
  automatically. Once closed, the session accepts no further extractions and the
  download is enabled. `5` is a single named constant, not scattered.
- **`file_path` is retired.** The column stays for now (nullable, unused) to avoid
  a destructive migration; new code never reads or writes it.

## Consequences

- **Positive**: fixes the extraction crash by removing the disk dependency
  entirely; no server-side file lifecycle, so the backend stays stateless and
  container-friendly; one source of truth (`extraction_records`); export cost is
  paid once at the end, not O(n) per row; the user actually gets their file via a
  real download.
- **Negative / trade-offs**: the exported `.xlsx` does **not** preserve the
  original template's look (titles, styles, header rows 1–3) — only column names
  and data. If fidelity is needed later, it is a separate, additive change
  (option A below). The hard cap of 5 rows is a product limit, not a technical
  one.
- **Neutral**: the `excel_data` named volume mentioned in ADR-0010 becomes
  unnecessary for this flow. `dataframe_json` and `file_path` remain in the schema
  as dead columns until a later cleanup migration.

## Alternatives considered

- **Keep writing the full `.xlsx` to disk after each row (status quo)** — rejected:
  this is the design that produced the bug; it needs a writable, persistent volume
  and still lacks a way to hand the file back to the user.
- **Option A — preserve the original template by storing its bytes.** Persist the
  uploaded `.xlsx` bytes (DB or object store) and reopen them in memory at export
  to keep formatting/header rows. Rejected for now: more storage and complexity for
  fidelity the current product does not require; can be added later without
  changing the export contract.
- **Object storage (S3/MinIO) for generated files** — rejected: overkill for a
  capture session whose output is produced once and downloaded immediately;
  reintroduces a file lifecycle we are deliberately removing.
