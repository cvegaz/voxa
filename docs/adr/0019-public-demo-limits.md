# 0019. Public demo limits (cost containment for an anonymous, internet-facing demo)

- **Date**: 2026-08-14
- **Status**: Accepted
- **Amends**: [ADR-0014](0014-audio-capture-constraints.md) — **how** the recording
  cap is enforced. The 20 s value itself stands (see §1).

## Context

Voxa is about to be exposed to the internet as an **anonymous public demo**. Every
visitor who narrates spends real money from the owner's OpenAI account (ADR-0007):
Whisper per second of audio, plus `gpt-4o-mini` for enrichment and extraction. The
deployment plan (shared with playPro Stats) names this as the one Voxa-specific
prerequisite before going live.

Three facts shape the decision:

1. **The audio duration cap is currently unenforceable.** ADR-0014 decided a 20 s
   cap "enforced in both layers", and explicitly rejected client-only enforcement
   because "an upload (or a tampered client) bypasses it, and the server pays the
   Whisper cost anyway". The implementation does not realize that intent:
   `transcribe_audio` receives `duration` as a **form field** and `AudioValidator`
   validates that number, not the file. The only check against the bytes is
   `size == 0`. The attack surface is the endpoint, not the UI — it accepts
   `wav`/`mp4`/`mpeg` regardless of what the browser recorder produces.

2. **File size cannot bound duration.** A legitimate 10 s WAV (44.1 kHz, 16-bit,
   mono) is ~880 KB, so a byte cap permissive enough to accept it (~1–2 MB) also
   accepts ~17 minutes of Opus encoded at 8 kbps — roughly 100× the cost of a
   normal narration. Bitrate is attacker-controlled; bytes bound bandwidth, and
   OpenAI bills seconds.

3. **The demo has no accounts.** Per-IP limits are the only identity available,
   and they are weak in both directions: CGNAT makes whole populations of mobile
   users share one address, and a VPN rotates it trivially. Account-based limits
   are the defensible ones (`todo.md` #11) but require verified email, which
   requires a sending domain that has not been purchased yet.

The owner's objectives frame the budget: this is a **portfolio and lead-generation
asset**, not a revenue product. The month-one goal is to observe real usage and
adapt monthly. The stated ceiling is **USD $10 per month**.

## Decision

### 1. Recording cap: 20 seconds — kept, but finally enforced and communicated

A 10 s cap was considered and **rejected on analysis** (2026-08-14): the number was
never the problem, the enforcement was.

Dictating one record at data-dictation pace is slower than conversational speech —
a phone number spoken digit by digit is ~4–5 s, a full date ~4 s. A record carrying
a name, a date, a phone and two more fields runs **15–20 s** in Spanish. The free
tier is defined as **8 fields** (`todo.md` #11), which 10 s cannot carry at ~1.25 s
per field. A 10 s cap would truncate a large share of *legitimate* narrations
mid-sentence.

Whisper bills the audio's **actual** duration, so the cap bounds the worst case, not
the typical one — a 7 s narration costs the same under either cap. Doubling the
ceiling roughly doubles only the adversarial maximum, which the per-IP limit and the
spend ledger already bound.

The failure modes are asymmetric, and that decides it: a cap that is too long costs
a few dollars inside a hard ceiling; a cap that is too short cuts a visitor off
mid-word, yields a wrong extraction, and loses the evaluation — at the exact moment
someone is judging whether this software works.

What changes, then, is that the cap becomes **real** and that the user is **told
about it**. It is enforced in three layers with **distinct responsibilities** — not
three copies of the same check:

| Layer | Responsibility | Nature |
|---|---|---|
| Recorder auto-stop | Show the countdown, stop the recording | **UX**, not security |
| Byte cap (4 MB) | Reject oversized uploads before decoding them | Protects **our** server (memory, temp files, subprocesses) |
| Real duration probe (`ffprobe`) | Reject audio longer than the cap | The **actual** cost control |

The duration probe measures the file, never the client's claim. The client-supplied
`duration` form field stops being a security input.

The byte cap is sized to admit the most bloated format we accept — a 20 s WAV at
44.1 kHz/16-bit stereo is ~3.4 MB — hence **4 MB**. That it is far too loose to
bound duration is exactly the point: it is a pre-filter, and the probe is the
control.

**The recorder must communicate the budget.** Today no UI string mentions a
duration at all, so the auto-stop arrives as a surprise. The limit is stated
*before* recording, the remaining seconds are visible *during*, and the final
stretch warns visibly. A silent cut mid-word is precisely the failure this decision
exists to avoid — the cap is a budget the user should be able to pace against, not
a trap.

`ffprobe` (from `ffmpeg`) is chosen over header-parsing libraries because the primary
format fails there: `mutagen` does not support WebM, and Chrome's `MediaRecorder`
writes WebM progressively, commonly leaving the duration element absent or zero
because it is unknown when the header is written. Reading the stream is required.

The probe enters behind an **injectable seam**, following the pattern the OpenAI
services already use (an optional client in the constructor). The test suite must
keep running without `ffmpeg` installed, and no assertion may be weakened to
achieve that (ADR-0009).

### 2. Anonymous trial: 1 template, 3 narrations

Enough to reach the "aha" moment, bounded enough to price. The existing 5-row
session cap is superseded for anonymous use by this smaller allowance.

### 3. A USD-denominated budget, counted in operations

Operations (transcription, enrichment, extraction) are counted **deterministically**
in Postgres and priced against **configured per-operation unit costs**, producing an
estimated spend ledger compared to a USD ceiling. This keeps counting exact and
testable while denominating the limit in the unit the owner actually cares about;
when OpenAI changes prices, the unit costs are configuration, not code.

Estimated unit economics. Whisper is ~$0.006/min, so the audio term scales with how
long people actually talk — the two columns are the *expected* case and the
*saturated* one, not two different products:

| Item | Typical (~8 s spoken) | Saturated (20 s) |
|---|---|---|
| Transcription (Whisper) | ~$0.0008 | ~$0.0020 |
| Extraction (`gpt-4o-mini`) | ~$0.0004 | ~$0.0004 |
| Enrichment (once per session) | ~$0.0005 | ~$0.0005 |
| **Full anonymous session** (1 template + 3 narrations) | **~$0.004** | **~$0.008** |

The cap's cost effect lives entirely in that second column. A 10 s cap would have
bought ~$0.005/session saturated — roughly 500 extra sessions of headroom on the
operating budget, at the price of truncating legitimate narrations.

Derived budget from the $10/month ceiling, sized on the **saturated** case so the
ceiling holds in the worst case:

| Bound | Value | Rationale |
|---|---|---|
| Monthly hard ceiling | **$10.00** | Owner decision; the real stop |
| Monthly operating budget | **$7.00** (~900 saturated / ~1,750 typical sessions) | What the demo may spend unattended |
| Manual headroom | **$3.00** | Released by editing configuration when the data shows legitimate demand hit the wall |
| Daily cap | **~$0.45** (~58 saturated sessions) | ~2× the daily average, so a good day is not punished |
| Per-IP cap | **10/hour, 20/day** on billable endpoints | Blunts trivial floods; a legitimate 3-narration trial never approaches it |

The daily cap deliberately exceeds `monthly ÷ 30`. It exists to bound the **blast
radius of one bad night**, not to ration the month; the monthly ceiling is the
real stop. A saturated month therefore exhausts the operating budget before day 30
— which is the intended behavior, because **exhausting the budget is a success
signal that triggers a configuration change, not a failure to prevent**.

**Reserved capacity is manual, not automatic.** An automatic bulkhead between
"anonymous" and "identified" traffic is not buildable without verified identity —
anyone typing an email would enter the privileged pool, and the partition would
protect nothing. At this scale an operator reacting within a day beats a mechanism
that cannot be trusted.

### 4. Limits are configuration, not code

Every cap above is read from the environment at startup. Adapting month to month
must be an `.env` edit and a restart, never a rebuild and redeploy. This extends the
override habit ADR-0014 established.

### 5. Email capture is a soft gate that grants nothing

The email is requested at two moments of demonstrated interest — **on download** and
**on hitting the quota wall** — and the `.xlsx` downloads regardless. It is stored
unverified and **grants no additional quota**: an unverified email that buys quota is
a trivial Sybil hole (fabricate identities to evade per-identity limits). The data is
treated as *leads to qualify*, never as confirmed contacts.

Verified email — and the accounts that unlock the real free tier (`todo.md` #11) —
are deferred until a sending domain exists.

### 6. Capability detection, not browser detection

Before recording, the frontend verifies that `MediaRecorder` and a usable mime type
are available, and explains the problem in the session language if not. We do **not**
sniff the user agent and do **not** recommend a browser: user-agent strings are
self-reported and the compatibility table rots. This also avoids paying for a
transcription of audio that was never going to be usable.

### 7. Funnel traceability

Each session records its progression (started, first narration, download, wall hit)
plus browser and platform. Without it, a silent failure on an unsupported device is
indistinguishable from disinterest, and the month's headline metric — the rate of
sessions reaching a first narration — is unreadable. The column names of uploaded
templates are retained as an industry signal.

### 8. Privacy notice becomes mandatory

Storing an email alongside voice makes the data identifiable. A privacy notice
(what happens to the audio, that it is sent to OpenAI, what is retained and for how
long, what the email is used for) must exist **before** the demo is public. This
promotes `todo.md` C.4 from backlog to release blocker.

### 9. Rate limiting must survive the reverse proxy

Behind Caddy, `slowapi`'s `get_remote_address` sees the proxy's address, so every
visitor would share one bucket. The client address must be resolved from the
forwarded header with the proxy explicitly trusted; otherwise the per-IP limit is
inert precisely in production.

## Consequences

- **Positive**: the monthly bill has a hard, owner-set ceiling; a single bad night
  cannot drain the month; the recording cap becomes a real control instead of a
  client-side suggestion; the month produces decision-grade data instead of an
  anecdote; the tuning loop is a configuration edit.
- **Negative / trade-offs**: `ffmpeg` grows the backend image (~100–250 MB, on an
  image already carrying `pandas`); the duration probe makes `AudioValidator`
  impure and requires an injectable seam; the budget ledger adds a table and a
  write on the hot path; unverified emails carry a real junk rate; a saturated
  month goes quiet until the owner raises the caps.
- **Neutral**: the anonymous allowance and every cap are provisional by design —
  they are expected to move monthly as real data arrives.

## Alternatives considered

- **Lowering the cap to 10 s** — rejected (§1): it would truncate legitimate
  narrations, since one record with a date and a phone number takes 15–20 s to
  dictate and the free tier is 8 fields. It buys ~500 sessions of headroom that the
  demo's realistic traffic does not need, in exchange for the worst failure mode
  available — a visitor cut off mid-sentence while evaluating the software.
- **Byte cap only, no `ffprobe`** — rejected: size cannot bound duration when the
  adversary picks the bitrate, and an operations-counted budget would stop
  predicting cost the moment someone maximizes seconds per operation.
- **Monthly budget only, no daily cap** — rejected: one scripted night drains the
  month and the demo is dark for three weeks.
- **Accounts before launch** — rejected for now: verified email needs a sending
  domain that is not purchased, and the account system (verification, sessions,
  recovery, bilingual UI) is a far larger unit of work than the gate that unblocks
  deployment. It remains the freemium's first step.
- **Signup wall before the first narration** — rejected: it filters out the
  qualified-but-cautious visitor at exactly the moment the demo is supposed to feel
  effortless, and an unverified wall is worse than an IP limit for abuse control.
- **Automatic reserved pool for identified users** — rejected: unbuildable without
  verification; replaced by manually released headroom.
- **Recommending a browser** — rejected: it is a self-reported signal that does not
  touch the threat model, and it makes a marketing demo read as unfinished.
