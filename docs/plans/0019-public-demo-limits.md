# Implementation plan — Public demo limits

Realizes **[ADR-0019](../adr/0019-public-demo-limits.md)**. Makes Voxa safe to expose
to the internet anonymously: the recording cap becomes real, spending gets a hard
ceiling, and the month produces readable data. TDD per ADR-0009 — write or update the
test alongside each change; the suite stays offline and must run **without `ffmpeg`
installed**.

**Decisions locked (ADR-0019):** the **20 s** cap stays (re-examined and kept — a 10 s
cap would truncate legitimate narrations) but is verified server-side with `ffprobe`
behind an injectable seam **and communicated in the UI**; anonymous trial = 1 template
+ 3 narrations; USD-denominated budget ($10/month hard, $7 operating, $3 manual
headroom, ~$0.45/day) counted in operations priced by configured unit costs; per-IP
10/hour and 20/day on billable endpoints; email captured as a soft gate that grants no
quota; capability detection, no browser sniffing; every cap is configuration.

**Numbering note (resolved):** when this plan was written `backend/migrations/`
held **two** `006_*` files (`add_session_language`, `create_contact_messages`), so
the migrations below took **007–009**. The collision was fixed afterwards in
`todo.md` → *Track 3*: `create_contact_messages` became **010**, the ones below
kept their numbers, and `scripts/migrate.py` now refuses to run when two
migrations share a number. Final order on a fresh database: 001→010.

---

## Phase 1 — Make the cap real

Goal: the server rejects long audio based on the **file**, never on the client's word.

- [x] `app/constants.py` — `MAX_AUDIO_DURATION_SECONDS` **stays 20.0** (ADR-0019 §1
      kept the value); add `MAX_AUDIO_BYTES` (default 4 MB — a 20 s stereo WAV is
      ~3.4 MB). Both read from the
      environment with these defaults (ADR-0019 §4).
- [x] New `app/services/audio_probe.py` — `AudioDurationProbe` wrapping `ffprobe`,
      returning measured seconds and raising a domain exception when the file is
      unreadable/corrupt. Run the subprocess **without blocking the event loop**.
- [x] `AudioValidator` — accept an **optional probe** in the constructor (same seam
      as the OpenAI services: `None` → build the real one). Order of checks:
      not-empty → byte cap → MIME type → **measured** duration.
- [x] `transcription_routes.transcribe_audio` — stop treating the `duration` form
      field as a security input. Keep accepting it for telemetry/UX only, or drop it;
      the validator no longer consults it.
- [x] Reject unreadable audio with a flattened `422` + `errorCode` the frontend can
      localize (`AUDIO_UNREADABLE`).
- [x] `backend/Dockerfile` — install `ffmpeg` (`--no-install-recommends`) in the
      image.
- [x] Tests: a stub probe injected in unit tests (**suite must not require
      `ffmpeg`**); a file whose real duration exceeds the cap is rejected **even when
      the client reports a compliant `duration`** — this is the regression test that
      encodes ADR-0014's original intent; oversized bytes rejected before the probe
      runs; corrupt file → `AUDIO_UNREADABLE`.

## Phase 2 — Say the limit, pace it, and detect capability before recording

Goal: the user is told the cap and can pace against it, and an unsupported browser
fails loudly rather than silently.

- [x] `AudioRecorder.tsx` — `DEFAULT_MAX_DURATION_SECONDS` **stays 20**. Re-comment
      the auto-stop as **UX, not enforcement**, cross-referencing ADR-0019 §1.
- [x] **Communicate the budget** (ADR-0019 §1) — today **no string mentions a
      duration at all**, so the stop arrives as a surprise:
      - state the limit before recording starts;
      - show progress against the limit while recording, as `elapsed / limit`
        (`00:03 / 00:20`) rather than a bare countdown — it is the convention every
        recorder already uses, and it keeps "how long is my narration" visible,
        which the user also needs;
      - warn visibly in the final stretch (~last 5 s) with the **remaining**
        seconds spelled out, since that is the moment pacing actually matters.
      Copy in `i18n/translations.ts`, ES + EN.
- [x] Capability check before recording: `MediaRecorder` present and a usable mime
      type supported. On failure show a clear localized message and do not offer
      recording. **No user-agent sniffing, no suggested-browser note** (ADR-0019 §6).
- [x] Localize the new backend error codes (`AUDIO_UNREADABLE`, `RATE_LIMITED`,
      `DEMO_BUDGET_EXHAUSTED`, `TRIAL_EXHAUSTED`) in both languages.
- [x] Tests (vitest): auto-stop fires at the cap; the cap appears in the rendered
      copy before recording; the final-stretch warning appears; capability failure
      renders the fallback instead of the recorder.

## Phase 3 — Rate limit what actually costs money

Goal: the per-IP limit protects the billable endpoints, and still works behind Caddy.

- [x] `app/rate_limit.py` — add configurable limits for billable endpoints
      (`BILLABLE_RATE_LIMIT_HOUR` default `10/hour`, `BILLABLE_RATE_LIMIT_DAY`
      default `20/day`).
- [x] **Resolve the client IP from the forwarded header with the proxy trusted.**
      Default `get_remote_address` sees Caddy's address in production, which would
      put every visitor in one bucket — the limit would be inert exactly where it
      matters (ADR-0019 §9). Trust the header only when a `TRUSTED_PROXY_IPS`-style
      setting says to, so a direct-exposure deployment cannot be spoofed.
- [x] Apply the limits to `POST /api/transcriptions/transcribe`, the extraction
      endpoint, and the template **confirm** endpoint (confirm triggers enrichment —
      it is billable).
- [x] Tests: limit enforced per endpoint; two different forwarded addresses get
      independent buckets; the forwarded header is **ignored** when the proxy is not
      trusted; 429 keeps the flattened error contract.

## Phase 4 — The spend ledger (daily + monthly ceilings)

Goal: a hard USD ceiling that survives restarts and cannot be drained in one night.

- [x] Migration `007_create_usage_ledger.sql` (+ `_rollback`): one row per billable
      operation — timestamp, operation type, estimated cost, session reference.
      Indexed for "sum since <instant>".
- [x] `app/services/usage_budget.py` — records an operation and answers "is there
      budget left?" for the day and the month. Unit costs and both ceilings come from
      the environment (`DEMO_COST_TRANSCRIPTION`, `DEMO_COST_EXTRACTION`,
      `DEMO_COST_ENRICHMENT`, `DEMO_BUDGET_DAILY_USD` default `0.45`,
      `DEMO_BUDGET_MONTHLY_USD` default `7.00`).
- [x] Check **before** the OpenAI call, record **after** it succeeds. Checking after
      would let each request overshoot by one operation.
- [x] Exhausted → flattened `429`/`503` with `errorCode: DEMO_BUDGET_EXHAUSTED` and
      copy that invites leaving an email (Phase 6), not a dead end.
- [x] Tests: day boundary rollover; monthly ceiling blocks even when the day is
      fresh; a failed OpenAI call does not consume budget; costs stay exact
      decimals. **Not tested, because not implemented:** "concurrent requests
      cannot both pass the last unit of budget". The check→call→record flow leaves
      a TOCTOU window, accepted deliberately — the overshoot is bounded by
      in-flight concurrency on a single process (fractions of a cent), and closing
      it would need a reservation protocol with compensating writes. Documented in
      `usage_budget.py`; the OpenAI account cap is the real backstop.

## Phase 5 — The anonymous allowance

Goal: 1 template + 3 narrations, then the wall that converts.

- [x] `constants.py` — the allowance is **3**, read from the environment as
      `ANONYMOUS_MAX_NARRATIONS`. **Reconciled into ONE constant**, not two:
      `MAX_ROWS_PER_SESSION` now *is* the anonymous allowance. Adding a second
      constant was rejected — with no accounts there is no second population to
      hold to a different number, and two constants where only one can apply
      eventually gets edited on the wrong side. When accounts land, paid tiers
      become a per-plan lookup and this stays the anonymous default.
- [x] Enforce in the extraction path: at the allowance the session finalizes with
      `errorCode: TRIAL_EXHAUSTED`.
- [x] The wall's copy (ES/EN) offers the email capture and still allows the download
      of what was already captured.
- [x] Tests: the 4th narration is refused; the download of the first three still
      works after exhaustion.

## Phase 6 — Email soft gate (leads, not keys)

Goal: capture interest at the two moments of demonstrated value, grant nothing.

- [x] Migration `008_create_demo_leads.sql` (+ `_rollback`): email, capture point
      (`download` | `wall`), session reference, locale, timestamp. Follow the
      `contact_messages` shape and its repository pattern.
- [x] Endpoint to record a lead — rate-limited, honeypot, format validation only.
      **Explicitly no verification and no quota granted** (ADR-0019 §5).
- [x] Frontend: optional email field on the download step and on the exhaustion
      wall. **The `.xlsx` downloads either way** — the field is never blocking.
- [x] Tests: submitting a lead does not change any remaining quota; download works
      with the field left empty; malformed email rejected without losing the download.

## Phase 7 — Funnel traceability

Goal: at month's end, distinguish "nobody cared" from "it silently broke".

- [x] Record per session: started, first narration completed, download, wall hit,
      plus browser and platform. Reuse the session row where possible instead of a
      new event table if that keeps it simple.
- [x] Retain uploaded template **column names** as the industry signal (ADR-0019 §7).
      **No new column added** — `template_sessions.schema_json` already holds them,
      so the report derives the signal from there. A second copy would be free to
      drift from the first.
- [x] A small read-only summary (a query or script is enough — no dashboard) that
      answers: sessions, aha rate, downloads, leads, walls hit, spend, **cost per
      captured lead**.
- [x] Tests: each transition is recorded exactly once.

## Phase 8 — Release blockers before the demo is public

- [x] **Privacy notice** (ES/EN) reachable from **both** the app and the landing.
      The app's is the full one (voice → OpenAI, what is discarded vs kept, the
      optional email, the funnel telemetry including the column-names/never-values
      distinction, retention, ARCO rights). The landing's is narrower — its contact
      form is the only collection point there — and it **points at** the app's
      instead of copying it, so the two cannot drift apart.
- [x] `backend/.env.example` — document every new variable with its default and the
      one-line reason it exists.
- [x] `README.md` / `CLAUDE.md` — document the demo limits and where to tune them.
      The **broken image reference** at the top of the README was the first thing a
      visitor to the public repo saw; `docs/assets/demo.gif` still does not exist,
      so the tag is now commented out with the instructions to restore it once the
      GIF is recorded (tracked in `todo.md` → *Track 4*). A missing image costs
      less than a broken one.
- [ ] **OWNER ACTION** — confirm the OpenAI account's own monthly spending cap is
      set. The last line of defence, outside the application: the in-app ledger
      protects against demo traffic, but only the account cap protects against a
      leaked key or a bug in the ledger itself.

---

## Out of scope (deliberately)

- **Accounts and verified email** — blocked on a sending domain; the freemium's first
  step (`todo.md` #11), not this deliverable.
- **Automatic reserved pool** for identified users — unbuildable without verification
  (ADR-0019 §3); the $3 headroom is released by hand.
- **Raising the paid-tier caps** (`todo.md` #9) — the configuration seam this plan
  adds is what will make that a config change later.
