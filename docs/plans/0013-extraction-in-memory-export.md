# Implementation plan — In-memory rows + on-demand Excel export

Realizes **ADR-0013**. Replaces the per-row write-to-disk extraction path with an
in-memory working set and a single on-demand export. TDD per ADR-0009: write or
update the test alongside each change.

**Decisions locked (ADR-0013):** export is reconstructed from the schema (no
template formatting, option B); the session closes on **Finalize OR 5 rows**,
whichever comes first.

---

## Phase 1 — Backend: stop touching disk in the extraction path

Goal: extraction succeeds with no `file_path` and no `.xlsx` on disk.

- [ ] `ExtractionOrchestrator.process` — remove steps 5–7 (DataFrame build,
      `update_dataframe`, `ExcelWriter.write`). It now: get session → build prompt
      → call LLM → parse → `save_extraction` → return `ExtractionResult`.
- [ ] Stop reading `session["file_path"]` and `dataframe_json` in the orchestrator.
- [ ] **Derive `row_number` from `count_records()` AFTER the save**, not from a
      parallel counter. The old order committed `dataframe_json` (step 6) *before*
      `save_extraction` (step 8), so failed attempts inflated the counter and the
      two stores desynced (observed live: `dataframe_json` = 2 rows while
      `extraction_records` = 0). With `extraction_records` as the single source,
      "save → count" is consistent and consecutive: each recording appends exactly
      one row and the next goes to the next number.
- [ ] `extraction_routes.process_extraction` — drop the `FileNotFoundError` /
      `OSError` branches that only existed for disk writes (keep LLM + generic).
- [ ] Tests: update `test_extraction_orchestrator.py` and
      `test_extraction_process_endpoint.py` — remove `file_path`/excel-writer
      expectations; assert no disk I/O occurs.

## Phase 2 — Backend: row cap + finalize (close the session)

Goal: a session closes on Finalize **or** at 5 records.

- [ ] Add `MAX_ROWS = 5` constant (single home, e.g. a config/constants module).
- [ ] Migration `004_*`: extend `chk_status` to allow `'finalized'` (+ its
      `_rollback.sql`). Keep `file_path`/`dataframe_json` columns (dead, per ADR).
- [ ] Repository: `count_records(session_id)` and
      `mark_finalized(session_id)`.
- [ ] In `process`: after saving, if `count == MAX_ROWS` set status `finalized`;
      reject a new extraction when status is already `finalized`
      (422 `SESSION_FINALIZED`).
- [ ] `POST /api/extraction/finalize/{session_id}` → mark finalized, return status
      + row count. Idempotent.
- [ ] Tests: cap enforcement (5th row finalizes; 6th rejected), manual finalize,
      double-finalize idempotency.

## Phase 3 — Backend: on-demand Excel export

Goal: download a `.xlsx` built in memory from schema + records.

- [ ] New service `ExcelExporter.build(schema, records) -> bytes`: openpyxl
      workbook in `BytesIO`; row 1 = column names (schema order), rows 2+ = data.
      No template formatting (ADR option B).
- [ ] **The export must NOT carry the template scaffolding rows.** The uploaded
      template uses row 2 = `Tipo_Dato` (`data_type`) and row 3 = `Ejemplo_Valor`
      (`example_value`); these are schema metadata only and must not appear in the
      final file. The exported sheet contains exactly: one header row of column
      names + the captured data rows. (Reconstructing from the schema satisfies
      this by construction — just assert it in the test so it can't regress.)
- [ ] `GET /api/extraction/export/{session_id}` → `StreamingResponse`
      (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`,
      `Content-Disposition: attachment; filename="<file_name>"`). 404 if no
      session; allow export even before finalize (current rows) — or restrict to
      finalized only (decide during impl; default: allow anytime).
- [ ] Tests: exporter unit test (headers, order, empty session, NA handling),
      endpoint test (content-type, disposition, bytes open as a valid workbook).

## Phase 4 — Frontend: finalize + download UX

- [ ] "Finalizar" button (always available) → calls finalize, then triggers
      download via blob from the export endpoint.
- [ ] Auto-close at 5 rows: when records reach `MAX_ROWS`, finalize automatically,
      surface a "límite alcanzado" message, and offer the download.
- [ ] Disable the record/accept controls once the session is finalized.
- [ ] Show a remaining-rows counter (e.g. "3 / 5").
- [ ] `extractionApi`: add `finalize(sessionId)` and `downloadExcel(sessionId)`.
- [ ] Tests (vitest): finalize call, auto-finalize at cap, controls disabled after
      finalize, download invoked.

## Phase 5 — Cleanup, infra, docs

- [ ] Remove `ExcelWriter` from the extraction wiring (delete the service if no
      other caller; keep its test only if the service stays).
- [ ] `docker-compose.yml`: drop the `excel_data` volume / uploads mount if present
      (no longer needed — ADR-0010 note).
- [ ] Update `CLAUDE.md` flow description and the
      `.kiro/specs/llm-extraction-excel-output/` design to match (reference
      ADR-0013).
- [ ] Frontend error map: show backend `detail` on 500s so future failures aren't
      masked by the generic message (the gap that hid this bug).

---

## Out of scope (deferred)

- Template-fidelity export (ADR-0013 option A: store original `.xlsx` bytes).
- Dropping the dead `file_path` / `dataframe_json` columns (later migration).
- Persisting finalized files / object storage.
