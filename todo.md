# TODO — Improvements for future versions

## Deployment (owner decisions, 2026-07-04 — shared plan with playpro_stats)

Staged AWS path recorded in
`../playpro_stats/docs/design/aws-deployment-plan.md`: Stage 1 = one EC2 with
Docker Compose + Caddy (HTTPS automatic), provisioned with Terraform from day
one in a NEW dedicated AWS account; Stage 2 = ECS Express Mode (App Runner is
in maintenance mode, closed to new customers 2026-04-30). Separate domain for
Voxa. **Voxa-specific pre-deploy work**: limit the public demo — per-visitor
(per-IP) rate limit AND a global per-day operation budget, plus the OpenAI
spending cap, so the free test cannot drain the API account.

**Status 2026-08-14** — pps has been live on this pattern since 2026-08-08, so
every artifact below already exists and works in `../playpro_stats`. Voxa's turn
is split in two tracks:

### Track 1 — Demo limits (the gate that makes public exposure safe)

Decided and specified: **[ADR-0019](docs/adr/0019-public-demo-limits.md)** +
**[plan](docs/plans/0019-public-demo-limits.md)**. Headline decisions: recording
cap **stays 20 s** but is **measured server-side** with `ffprobe` and stated in the
UI (the client-reported duration was never a real control); anonymous trial =
**1 template + 3 narrations**; spend
ceiling **USD $10/month** ($7 operating, $3 manual headroom, ~$0.45/day) counted in
operations priced by configured unit costs; per-IP **10/hour, 20/day** on billable
endpoints; email captured as a soft gate that **grants no quota**; capability
detection instead of browser sniffing; **every cap is configuration**, so monthly
tuning is an `.env` edit. Privacy notice is a release blocker.

### Track 2 — Production ✅ DONE (2026-08-15) — **live at https://tryvoxa.com**

Landing at the apex, demo app at `app.tryvoxa.com`, all three certificates issued
by Let's Encrypt on the first ACME attempt. Verified in production: routing for
all three hostnames, HTTP→HTTPS, the four security headers with the `Server`
banner gone, migrations 001→010 applied, the contact form persisting a row
through the apex, and `/api/schemas` at the apex returning the SPA rather than
the API. Deploys are automatic from here.

Two lessons worth keeping, both recorded in the deploy runbook:

- **Every `docker compose` command on the server needs `--env-file
  .env.production`**, not just `up`. `ps` and `logs` interpolate the same
  variables and fail with `required variable POSTGRES_PASSWORD is missing a
  value`, which reads exactly like a broken deploy while the stack is running
  fine.
- **For ~24 h after a DNS change your own machine is the worst witness.** The NS
  records carry a one-day TTL, so the local resolver kept serving Porkbun's
  nameservers after the registry had switched. Verification against the hostname
  returned a fully convincing wrong answer — `302`, `server: openresty`, and a
  valid Let's Encrypt certificate, all of it the registrar's parking page.
  Verify with `curl --resolve` against the Elastic IP instead.

Each item below had a working pps counterpart to adapt:

- [x] ~~`landing/Dockerfile` + `landing/nginx.conf`~~ **DONE 2026-08-14.** Two-stage
      build (node to compile, nginx:alpine to serve — 25 MB final image). One
      deliberate divergence from pps: Voxa's landing has a real contact form, so
      its nginx proxies **`location = /api/contact`** to the backend rather than
      being pure static. Exact match, not a `/api/` prefix — least privilege, so
      the apex does not become a second front door onto the billable
      transcription and extraction endpoints. Same-origin also means `VITE_API_BASE`
      stays empty, so **no CORS at all** and the image carries no domain (which
      matters: the domain is not bought yet, and a baked absolute URL would tie
      the artifact to it).
- [x] ~~`docker-compose.prod.yml`~~ **DONE 2026-08-14.** Postgres with no published
      port, `:?`-guarded secrets so a missing value refuses to boot rather than
      starting open, and every ADR-0019 limit surfaced as an overridable variable.
      Verified: only Caddy publishes host ports.
- [x] ~~`deploy/Caddyfile`~~ **DONE 2026-08-14.** Apex → landing, `app.<domain>` →
      SPA, `www` → 301, automatic HTTPS, shared security headers, an 8 MB
      edge body cap above the app's 4 MB audio limit, and a commented CSP to
      enable and test after the first deploy. `caddy validate` passes.
- [x] ~~`.env.production.example`~~ **DONE 2026-08-14** — every production variable
      with the reasoning, no real values.

      **Two defects found while verifying this batch, both fixed:**

      1. **`.env.production` was not git-ignored.** The rules were `.env`,
         `.env.local`, `.env.*.local` — none of which match `.env.production`,
         the file that holds the real `OPENAI_API_KEY` and `POSTGRES_PASSWORD`.
         Replaced with deny-all-then-readmit-templates (`.env.*` plus
         `!.env.example` / `!.env.*.example`), which fails safe: a future
         `.env.<anything>` is ignored by default instead of relying on someone
         remembering to add a rule.
      2. **nginx resolved the `backend` hostname at config-load time**, in both
         the landing and the pre-existing frontend config. Caught by the landing
         image refusing to start at all with no backend present. Two production
         failure modes: a crash loop under `restart: unless-stopped` (a static
         marketing site down because an API is slow), and — worse — a stale
         container IP cached forever after a redeploy, a permanent 502 that only
         a manual restart clears. Fixed with Docker's embedded resolver plus a
         variable in `proxy_pass`, which defers resolution to request time.
         **pps's `frontend/nginx.conf` has the same latent defect** and should get
         the same fix; noted in its deploy runbook.

      **Verified end to end**, whole stack on localhost with Caddy's internal CA:
      apex→landing 200, app→SPA 200, www 301, HTTP→HTTPS 308, all four security
      headers present and the `Server` banner gone; `POST /api/contact` through the
      apex reached the backend and **persisted a row**; `/api/schemas` at the apex
      returned the SPA (200) instead of the API, confirming the narrow proxy. And
      the hop-counting property: 33 POSTs each carrying a **different forged
      `X-Forwarded-For`** all landed in one bucket and the tail got 429 — a spoofed
      header cannot mint fresh quota.
- [x] ~~`.github/workflows/docker-publish.yml`~~ **DONE 2026-08-15.** Multi-arch
      (amd64 + arm64 via QEMU) build of the three images → GHCR → deploy via AWS
      SSM with OIDC. No stored AWS keys, no inbound SSH, nothing to rotate. Two
      tags per build: `latest` for the server to pull, and the commit SHA so a
      rollback is a one-line `.env.production` edit plus a restart.

      **One improvement over pps's version, from a failure this repo actually
      had:** pps triggers on `push: main`, which RACES CI — both start at once,
      so a merge whose tests are still running (or already red) publishes and
      deploys anyway. That happened here: the demo-limits PR was merged with 0
      of 3 checks finished. Voxa's uses `workflow_run` gated on
      `conclusion == 'success'`, making the pipeline sequential. Note the
      conclusion check is load-bearing — `types: [completed]` means "finished",
      not "succeeded". **pps should get the same fix**; noted in its runbook.

      The landing's `VITE_APP_URL` is passed as a build arg here rather than
      defaulted in the Dockerfile, so the image stays domain-agnostic and the
      deployment decides where "Try it yourself" points.

      **Verified**: `actionlint` clean on both workflows; all three images build
      for `linux/arm64` (the server's architecture) and report `linux/arm64`;
      and the built landing bundle really does contain `app.tryvoxa.com` with
      the `tu-usuario/voxa` placeholder gone — i.e. the CTA will be live.

      **OWNER ACTION** — set two repository *variables* (Settings → Secrets and
      variables → Actions → Variables). They are identifiers, not secrets; the
      OIDC trust condition is what gates access:

      | Variable | Value |
      |---|---|
      | `AWS_DEPLOY_ROLE_ARN` | `arn:aws:iam::275123487888:role/voxa-github-deploy` |
      | `SSM_INSTANCE_ID` | `i-0e4bb82ab4bf45264` |
- [x] ~~Domain~~ **`tryvoxa.com`, bought 2026-08-15.** Chosen after checking the
      field: `voxa.com` and `voxa.dev` are ACTIVE companies in adjacent AI/dev
      spaces, and `voxa.io` / `.ai` / `.app` are parked on premium marketplaces.
      `tryvoxa.com` unblocks the deploy for ~$11/yr without committing the
      brand — **the naming question stays open** (trademark search at IMPI/USPTO
      pending; a rename is cheap now and expensive once there is traffic).
      `voxa-core.com` was available and deliberately NOT bought: the product is
      Voxa, the engine is an implementation detail, and naming the apex after
      the engine inverts the hierarchy.

      Registered at **Porkbun**, not Route 53: registration failed twice on this
      AWS account, both rejected in under a second with an opaque message. The
      payment method was valid and setting the unset payment currency changed
      nothing, so a deterministic account-level block is the standing hypothesis
      (seller of record is AWS Mexico; `playprosystems.com` registered fine six
      days earlier). Support case open. DNS still lives in Route 53 — registrar
      and DNS host are separate services — so Terraform manages the records
      exactly as it does for pps.
- [x] ~~Terraform for Voxa~~ **DONE and APPLIED 2026-08-15**: 18 resources, its
      own EC2 (`i-0e4bb82ab4bf45264`, t4g.small, mx-central-1c), Elastic IP
      `78.13.12.185`, all three A records resolving, SSM agent Online, cloud-init
      done with Docker 29.1.3. State key `voxa/stage1`, cost tag `Project=voxa`.

      **Its own EC2, not the pps host** (decided 2026-08-14). The deciding factor
      is blast radius, not cost: pps serves a paying client, and a shared host
      couples that client's availability to a portfolio project's deploys,
      restarts and public-demo load. Sharing saves a few dollars a month and buys
      a coupling that is expensive to undo later — the same reasoning that moved
      Voxa to its own OpenAI project. A shared budget, like a shared host, is a
      shared failure domain.

      Running cost ≈ **$20/month** — above the ~$15 first estimated. The miss was
      the public IPv4 charge (~$3.65/mo), which AWS has applied to *every* public
      address, attached or not, since February 2024.
- [x] ~~`LANDING_ORIGINS`, strong `POSTGRES_PASSWORD`~~ **DONE 2026-08-15.**
      `LANDING_ORIGINS` is empty by design (the landing is same-origin through
      its own nginx, so no CORS is involved at all); `POSTGRES_PASSWORD` was
      generated with `openssl rand -base64 24` and never typed by a human.
- [ ] **Decide whether `/docs` stays public.** Currently it does — `GET
      https://app.tryvoxa.com/docs` returns 200. For a portfolio project that is
      arguably a feature: the API is self-documenting and the repo is public
      anyway. But it also hands an attacker a complete map of the billable
      endpoints and their exact payloads, which is a convenience worth pricing
      deliberately rather than by default.
- [ ] Daily `pg_dump` to S3 with one restore drill; uptime monitor; billing alarm.
      **Now the highest-value item left in this track**: the bucket and the
      server's write-only permission exist, but nothing writes to them on a
      schedule. This database holds the captured leads and the funnel history,
      which is the whole answer to "did the month work" — and a backup that has
      never been restored is a hypothesis, not a backup.

### Track 4 — Landing & distribution (the month depends on this more than on the limits)

> The demo limits make the month **safe**; the funnel instrumentation makes it
> **readable**. Neither makes it **happen**. The realistic failure mode of the
> whole exercise is not a runaway bill — the $10 ceiling holds — it is finishing
> the month with six sessions and concluding the product does not interest
> anyone, when what was missing was traffic. Items 1–3 below are already listed
> in Phase B.4; they are repeated here because their priority is wrong down
> there.

- [x] ~~**CTA hierarchy in the hero**~~ **DONE 2026-08-15** (added after the
      Track 4 discussion; it was not on this list and outranks everything that
      was). The demo is now the **primary** action ("Pruébalo tú mismo"),
      contact is a clear secondary, GitHub is tertiary. Product-led rather than
      sales-led, for a specific reason: Voxa is hard to describe and obvious to
      see — "captura de datos por voz" means nothing read, and thirty seconds of
      narrating means everything. It also makes the ADR-0019 §7 funnel
      instrumentation worth having, since aha rate, downloads and walls measure
      nothing while the demo sits behind a hidden ghost button.

      Under the buttons: *"Sin registro · 1 plantilla y 3 narraciones · ~2
      minutos"*. Removes the friction that suppresses the click, and means the
      wall is not a surprise when a visitor reaches it. Keep it in sync with
      `ANONYMOUS_MAX_NARRATIONS`.

      With no app URL configured the hierarchy falls back to contact-primary and
      the note disappears — a headline button pointing nowhere is worse than one
      fewer button. Five tests in `Hero.test.tsx` cover both configurations, the
      trial note, and `rel=noopener` on the new-tab link.
- [x] ~~**`og-image.png` in `landing/public/`**~~ **DONE 2026-08-15.** 1200×630,
      built from `landing/design/og-image.svg` (committed, with a README on
      regenerating it — a PNG with no source is a dead end). Uses the brand
      tokens and the favicon's mic glyph: wordmark, headline, and the
      voice→row visual that shows the product in one glance.

      **Found while doing it**: `og:image` was `/og-image.png`, a RELATIVE path.
      Open Graph crawlers do not resolve relative URLs — so the card would have
      rendered blank even once the image existed, and the failure would have
      looked like a missing file rather than a malformed tag. Now absolute, plus
      `og:url`, `og:site_name`, `og:locale`, `og:image:width/height`,
      `og:image:alt` and the twitter:* pair. Verified the absolute URLs survive
      the production build.
- [ ] **Fill `landing/.env`** — partially done 2026-08-14: `VITE_GITHUB_URL`
      now points at the real repo (`cvegaz/voxa`); it defaulted to the
      placeholder `https://github.com/tu-usuario/voxa`, i.e. the landing linked
      to a repo that does not exist. The deployed app URL is now supplied as a
      **build arg** in `docker-publish.yml`, and `VITE_PLAYPRO_URL` has a real
      default. Still empty: LinkedIn and Calendly. Note the file is git-ignored,
      so the deployed build needs these injected at build time, not copied from a
      developer machine.

      **`VITE_CONTACT_EMAIL` stays empty deliberately** (2026-08-15). Publishing
      an address in the bundle gets it harvested within days, and the only
      address available today is a personal one. It is also unnecessary: the form
      persists every submission regardless, and `CONTACT_NOTIFY_EMAIL` —
      **server-side config nobody sees** — now delivers the notification (Gmail
      app password, verified end to end before deploying). The public address and
      the notification address are separate decisions, and only the public one
      waits on settling the brand. When it settles the answer is an **alias** on
      the domain forwarding to the personal inbox — address ≠ account, no new
      mailbox to check — with its MX records added to `dns.tf` so they are
      versioned like everything else.
- [ ] **Record the demo GIF/video** — and drop it at `docs/assets/demo.gif`,
      which the README already references and which **does not exist**, so the
      public repo opens with a broken image (see Phase 8 of the ADR-0019 plan).
- [x] ~~**Link the playPro Stats case study to the live product**~~ **DONE
      2026-08-15.** The card claimed pps was built as a configuration over the
      Voxa core and named a real client, with no way to check either. It now
      links to `https://app.playprosystems.com` — the app, not
      `playprosystems.com`, because the claim is about the *product* and its
      marketing site is not evidence of it. pps's reads are public, so a
      visitor sees real games without an account. Both URLs verified live (200)
      before linking; a dead link here would cost more credibility than the
      claim buys. Styled as a quiet link rather than a button so the page's
      primary action stays with the demo.
- [ ] **Decide where the landing gets published** — a marketing site nobody links
      to is a marketing site nobody sees. Concrete channels beat "we'll share it":
      the GitHub profile README, a LinkedIn post built from the ADRs (the
      engine-extraction story is written already), and the pps case study.
- [x] ~~Set backend `LANDING_ORIGINS` to the real landing origin once it is
      live.~~ **RESOLVED 2026-08-15 — it stays EMPTY**, which is better than
      setting it. The landing's nginx proxies `/api/contact` to the backend on
      the internal network, so the request is same-origin and no CORS allowlist
      is involved at all. The variable remains supported for the case where the
      landing is ever hosted off-host (S3+CloudFront, Vercel).

### Track 3 — Repo hygiene (found 2026-08-14, do before deploying)

> Three defects found while executing Track 1. None blocks local development;
> all three are the kind of thing a reviewer notices in a public repo whose
> selling point is engineering discipline. They share a fix shape: **the
> verification must run in CI, or it does not exist.**

- [x] ~~**`npm run lint` is a phantom command.**~~ **FIXED 2026-08-14.** eslint,
      `typescript-eslint` and the React plugins are installed in **both** apps,
      with a flat `eslint.config.js` each, and `ci.yml` now runs **lint and
      typecheck** before the tests in both jobs — which is the part that makes it
      real. Findings were triaged by hand (no blind `--fix`): one genuine
      `react-hooks/exhaustive-deps` hit in `AudioRecorder.tsx`, where the unmount
      cleanup effect sat *above* the `useCallback`s it called and worked only by
      accident; it moved below them and now lists its real dependencies. The three
      `react-refresh/only-export-components` warnings on the two `LanguageContext`
      files were **acknowledged rather than obeyed** — provider plus hook in one
      module is the standard context shape, and splitting them would export mutable
      module state across a boundary to buy back a dev-server nicety. Both apps
      lint clean.
- [x] ~~**The test suite has a hidden dependency on `OPENAI_API_KEY`.**~~ **FIXED
      2026-08-14** (confirmed live: the first CI run of the demo-limits PR failed
      on exactly this). `openai>=2` raises `OpenAIError: Missing credentials` from
      the client **constructor**, and the routes build their services eagerly — so
      a test that mocked the orchestrator and never intended to call OpenAI still
      exploded. `ci.yml` sets no environment variables, so CI failed while every
      developer machine with a key exported passed. Fix: the three OpenAI services
      now build their client **lazily**, on first use, preserving the injection
      seam. `tests/test_offline_suite.py` asserts the property directly, so a
      future service that constructs eagerly is caught locally instead of in CI.
- [x] ~~**No dependency pinning.**~~ **FIXED 2026-08-14, before deploying.**
      `backend/` now uses the abstract/concrete split: hand-written
      `requirements.in` / `requirements-dev.in` carry the intent, and
      pip-compile generates fully-pinned `requirements.txt` /
      `requirements-dev.txt` including transitive dependencies. The Dockerfile
      installs the runtime file only, so pytest and hypothesis no longer ship
      inside a container exposed to the internet. `openai` is capped below the
      next major deliberately. **Verified**: the pinned set was installed into a
      clean venv and the full suite passed there with an empty environment, and
      the call signatures of `audio.transcriptions.create` and
      `chat.completions.create` were checked against the pinned version — the
      offline suite would not have caught a signature change on its own.
- [x] ~~**Two migrations numbered `006`.**~~ **FIXED 2026-08-14, before
      deploying** — which was the last safe moment: renaming an applied migration
      is free while no production database exists and hazardous afterwards.
      `006_create_contact_messages` became `010_*` (the number is an apply-order
      sequence, not a historical record; git holds the history, and the table
      depends on nothing from 007-009). Its index gained `IF NOT EXISTS` so the
      rename is survivable on a database that already applied the old name. The
      durable half: `scripts/migrate.py` now **refuses to run** when two
      migrations share a number — verified by planting a duplicate. A fresh
      database applies 001→010 cleanly.

## Pending discussion and implementation

### 1. Record review & editing
- [x] **Post-accept verification (done, 2026-06-30)**: after "Aceptar", the narrated
  text stays visible (read-only) and the new row appears in the table, so the user
  can check that what they dictated was captured correctly.
- [ ] **Edit the extracted values** — show the LLM-extracted field values and allow
  correcting each one. Today a wrong extraction cannot be fixed from the app (the
  row is committed as-is). Could be a pre-commit confirm step and/or inline editing
  of an existing row.
- [ ] Decide whether the edit/confirm step is mandatory or a configurable option.

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

### 8. Multi-language infrastructure for end-to-end records — ✅ done for ES/EN (2026-06-30, ADR-0017)
> Goal: run the app in any language and process the record in that language end-to-end (not just the UI, #7). Implemented for **Spanish + English**; adding a third language means extending the prompt templates, the `date_normalizer` month tables, and the UI catalog (no architectural change).
- **Per-session language**: ✅ done — `template_sessions.language` (migration 006), **fixed when the template is confirmed** (the UI sends its language to `/confirm`). Transcription, enrichment, and extraction all read it.
- **Transcription**: ✅ done — `whisper_service.transcribe()` takes a `language` arg, and the transcribe route now uses the **session** language (`active_session.language`), not a per-request value.
- **LLM prompts**: ✅ done — `prompt_builder.build()` and `LLMEnrichmentService.enrich()` emit ES/EN templates **and are wired** to the session language (confirm → enrichment; orchestrator → extraction prompt). Tested ES+EN.
- **Schema data-type names**: ✅ sufficient for now — the only type-driven branch is date detection, and `is_date_type()` recognizes both Spanish "fecha" and English "date". A broader language-agnostic type enum is not needed until other types branch on language.
- **Locale-aware value parsing/formatting**:
  - Dates: ✅ done — the normalizer is language-aware: Spanish reads DD/MM and outputs `DD-mmm-YYYY` (`17-sep-2026`); English reads MM/DD and outputs `MM/DD/YYYY` (`09/17/2026`). Driven by the session language via `response_parser`.
  - Numbers: ✅ decided — left **as-is** (no normalization), to avoid mis-reading ambiguous separators (product decision, 2026-06-30).
  - Booleans: handled by the extraction prompt (the model returns the localized value / `"no"` for explicit absence); no separate normalization layer.
- **Enriched context language**: ✅ done — `Contexto_Enriquecido` is generated in the session language (enrichment runs in es/en at confirm time).
- **Error messages from the pipeline**: ✅ resolved by design — the frontend localizes by `errorCode` (ES/EN, ADR-0016), so the user always sees the right language. The backend `detail` strings stay Spanish on purpose (the frontend replaces them; they only show in logs/Swagger/rare passthroughs).
- **Tests**: ✅ ES+EN cases across the pipeline — Whisper language, prompt builder, enrichment, confirm endpoint, orchestrator, response parser, and date normalizer.
- **Docs**: ✅ ADR-0017 (per-session language + locale formatting), plus README and CLAUDE.md notes.

### 9. Tier-based recording limit
- The max audio recording length is **20s** — ADR-0019 re-examined it and **kept**
  ADR-0014's value (10s would truncate legitimate narrations: one record with a date
  and a phone number takes 15–20s to dictate). Enforced client-side as UX (auto-stop
  in `AudioRecorder`, now with a visible countdown and a final-stretch warning) and
  server-side as the real control (`AudioValidator` + a measurement of the file, not
  the client-reported duration).
- The limit is already configurable (a `maxDurationSeconds` prop on the recorder
  and a `max_duration_seconds` constructor arg on the validator, both defaulting
  to `MAX_AUDIO_DURATION_SECONDS` in `app/constants.py`).
- For a paid tier: source the cap from the user's plan and pass it through both
  layers, instead of using the single free-tier default.

### 10. Auto-generate a transcription vocabulary from the template (Whisper prompt)
- `voxa-core`'s `WhisperTranscriptionService.transcribe()` now accepts an optional
  `prompt` (vocabulary/style bias), but Voxa does not fill it yet.
- Idea: at template **confirm** time, derive a compact domain vocabulary from the
  template and store it on the session (like `enriched_context`), then pass it to
  Whisper on every transcription so domain terms and example values transcribe
  correctly (fewer mis-hears).
- Sources: (a) **deterministic** — column names + `Ejemplo_Valor` (cheap, always
  available); (b) **LLM** — piggyback on the enrichment call, which already asks for
  "sinónimos o variaciones de cómo un hablante podría referirse a cada dato", to
  also emit a ~20–40 term list. Hybrid recommended.
- Boundary: the generic "schema (+ context) → vocabulary string" capability belongs
  in `voxa-core` (next to the `prompt` hook); Voxa wires generate-on-confirm → store
  on session → pass to Whisper. Origin: playpro_stats ADR-0008 hand-wrote its FBA
  vocabulary; this generalizes it. Note: terse, code-style column names (like pps's
  `qb_no`) benefit less — field *descriptions* would feed a better LLM-generated list.

### 11. Freemium app + membership (owner direction, 2026-07-05)

> Voxa — unlike playpro_stats, whose capture app stays store-less — IS the
> right product for app-store presence and a freemium model: its users are
> unknown (store discoverability is a real channel), a consumer paying with a
> card values the store trust badge, and subscriptions are the category's
> standard monetization.

- **Free tier (owner-defined)**: max **8 fields** per template and ~**10
  entries** — a capability limit (shapes perception, feels complete but
  bounded) plus a usage limit (caps the real OpenAI cost: ~cents per free
  user, sustainable acquisition cost). Open sub-decision: entry-limit
  cadence — lifetime trial vs **monthly reset (recommended: retention/habit
  beats one-shot trial pressure)**.
- **Membership**: unlocks feature gates. Candidates: >8 fields, more/unlimited
  entries, longer recordings (generalizes #9's tier-based 20 s cap),
  multiple records per audio (#3), persistent enriched context (#4),
  export/API options.
- **Prerequisites (build order matters)**:
  1. **User accounts** — Voxa is fully anonymous today; account-based limits
     are the only defensible ones (IP limits are trivially evaded). The pps
     Stage-A auth (JWT + bcrypt, its ADR-0016) is the harvestable pattern.
  2. **Entitlement layer**: plan → limits (fields, entries, seconds,
     features), enforced server-side; usage metering per account.
  3. **Payments**: web (Stripe — no store cut) vs in-app purchase (15–30%
     commission, frictionless). Likely web-first; decide at build time.
- **Distribution**: same staged logic as the pps field-capture plan — PWA
  first (validate), stores when monetization is live and discoverability
  starts paying. Store costs: Apple $99 USD/year, Google Play $25 USD
  one-time.
- **Relationship to the public demo limits** (Deployment section above):
  complementary layers, not the same thing — the anonymous web demo keeps its
  hard per-IP/per-day caps as a marketing teaser; the free TIER is an
  account with the 8-field/10-entry plan; membership lifts the gates.

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
- [x] ~~Set a monthly spending limit in the OpenAI dashboard as a safety net~~ **DONE
      2026-08-14** — and at the **project** level, not the account level, because both
      keys shared OpenAI's "Default project" and an account-wide cap would have
      throttled pps (a paying client) too. Voxa now has its own `voxa-demo` project:
      $15/month spend limit, alert at $9, allowed models restricted to `whisper-1`
      and `gpt-4o-mini`, 10 RPM on both. Key rotated, old one revoked. Full
      rationale in the [ADR-0019 plan](docs/plans/0019-public-demo-limits.md).

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

### B.4 Landing page (done — `landing/`)
- [x] Standalone static marketing site (Vite + React + TS), bilingual ES/EN, same brand
- [x] Sections: hero with animated voice→Excel mockup, how-it-works, features, the
  **playPro Stats** case study + "your domain?" hook, tech stack, contact form, footer
- [x] Contact form → `POST /api/contact` (Postgres + optional email, honeypot + rate-limit)
- [ ] Fill `landing/.env` with real links (GitHub, deployed app, LinkedIn, Calendly, email)
- [ ] Add an `og-image.png` to `landing/public/` and record a real demo GIF/video
- [ ] Deploy the landing (S3+CloudFront / Vercel / Netlify) and set backend `LANDING_ORIGINS`

## Phase C — Security for deployment and production

> Do ALL of this BEFORE exposing the app to the internet anonymously.

### C.1 Secrets and configuration (not in the repo)
- [ ] `OPENAI_API_KEY` and credentials are injected from the hosting provider's secrets manager (Railway/Render/Fly/AWS Secrets), NOT from a versioned `.env`
- [ ] Change `POSTGRES_PASSWORD: postgres` (docker-compose.yml:24) to a strong password sourced from secrets
- [ ] Production `DATABASE_URL` separate from the dev one

### C.2 Cost and abuse control (because you pay for every call)

> All of this is now specified in **[ADR-0019](docs/adr/0019-public-demo-limits.md)**
> and its **[plan](docs/plans/0019-public-demo-limits.md)** — Track 1 above.

- [~] Rate limiting in the backend (requests per IP/user per minute) — `slowapi` is
  now wired (`app/rate_limit.py`) and applied to `POST /api/contact`. Still pending:
  extend it to the OpenAI-spending endpoints (transcribe/extract/confirm), **and
  resolve the client IP from the forwarded header** — behind Caddy the default
  `get_remote_address` puts every visitor in one bucket.
- [ ] Size and duration limits for accepted audio in `transcription_routes.py` —
  note the duration is currently taken from a **client-supplied form field**, so
  the ADR-0014 cap is not actually enforced. Needs a byte cap plus a real
  measurement of the file.
- [ ] Global spend ledger with daily **and** monthly ceilings (a monthly-only cap
  can be drained in one night).
- [~] Authentication / login — **deliberately deferred**: verified email needs a
  sending domain that is not purchased yet. The demo stays anonymous, with the
  limits above standing in for identity. Accounts remain the freemium's first
  step (#11).
- [x] ~~Keep the monthly OpenAI spending cap active (last line of defense, outside
  the app)~~ **DONE 2026-08-14** — see A.1 above for the values and why it is scoped
  to Voxa's own OpenAI project rather than the whole account.

### C.3 Network exposure
- [ ] HTTPS required (most hosts provide it for free with a domain)
- [ ] Do NOT expose Postgres (5330) or the backend (5310) directly to the internet; only the frontend/proxy is public
- [ ] CORS locked down to the real frontend origins
- [ ] Review security headers and disable the public Swagger `/docs` if you do not want it

### C.4 Privacy (the app processes voice = personal data)

> **Release blocker, not backlog** (ADR-0019 §8): capturing an email alongside voice
> makes the data identifiable, so the notice must exist before the demo is public.

- [ ] Privacy notice (ES/EN): what is done with the audio, that it is sent to OpenAI, whether or not it is stored, and what the captured email is used for
- [ ] Decide and document whether the audio is deleted after processing or persisted
- [ ] Review what is stored in the `excel_data` volume and for how long

### C.5 Operations
- [ ] Basic logging and error monitoring
- [ ] Database backups
- [ ] Healthchecks and a restart policy in the deployment
