# 0014. Audio capture constraints (recording length and input quality)

- **Date**: 2026-06-29
- **Status**: Accepted

## Context

Each narration is transcribed by OpenAI Whisper, which **costs money per call**
(ADR-0007) and whose accuracy depends on input quality. Two issues motivated this
decision:

- Recordings were effectively long (auto-stop at 30s). Longer clips raise cost and
  latency, and the product is designed around short, single-record narrations.
- Bluetooth microphones are forced onto the low-fidelity HFP/HSP profile (mono,
  ~8–16 kHz) when used as an input device, which noticeably degrades
  transcription. The web platform cannot change that profile.

## Decision

We will constrain audio capture on two axes:

- **Recording length cap**: a single recording is limited to **20 seconds** on the
  current (free) tier. The limit is a single source of truth,
  `MAX_AUDIO_DURATION_SECONDS` in `app/constants.py`, and is enforced in **both**
  layers — client-side (the recorder auto-stops) and server-side (`AudioValidator`
  rejects longer audio) — so an uploaded file cannot bypass it. Both layers accept
  an override (a `maxDurationSeconds` prop and a `max_duration_seconds` constructor
  argument) so a **future paid tier can raise the cap** without code changes
  (see `todo.md` item #9).
- **Input-quality warning**: when the active input device looks like a Bluetooth
  mic (detected heuristically from the track label), show a **non-blocking**
  warning suggesting the built-in or a wired/USB mic for better accuracy.

## Consequences

- **Positive**: predictable, low cost per transcription; clips sized for the
  single-record flow; users are steered away from the most common accuracy
  pitfall.
- **Negative / trade-offs**: the cap is duplicated across two layers and must be
  kept in sync (cross-referenced in comments). Bluetooth detection is a
  label-based heuristic — it can miss or misclassify unusual device names.
- **Neutral**: the warning is advisory only; we never block recording on it,
  because we cannot reliably guarantee a device is Bluetooth.

## Alternatives considered

- **Enforce the limit only on the client** — rejected: an upload (or a tampered
  client) bypasses it, and the server pays the Whisper cost anyway.
- **Hard-block Bluetooth mics** — rejected: detection is not reliable enough to
  deny capture, and it would frustrate users whose Bluetooth audio is acceptable.
- **A fixed, non-configurable cap** — rejected: it would force a code change to
  support paid tiers; the override keeps tiers a configuration concern.
