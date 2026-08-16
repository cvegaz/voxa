/**
 * The hero mockup's choreography, kept out of the component so it can be read,
 * tuned and tested without touching JSX.
 *
 * The previous mockup was static markup animated by CSS `animation-delay`, which
 * plays once on load and freezes. Showing two narrations landing as two rows in
 * the same sheet needs state that evolves over time, so this is a small finite
 * state machine driven by one timer.
 */

/** One step of one record's cycle. */
export type Phase =
  | 'recording'
  | 'transcribing'
  | 'confirming'
  | 'committed'
  /** Both rows are in; hold the finished sheet before looping. */
  | 'resting';

export interface Step {
  phase: Phase;
  /** Which example this step belongs to (index into EXAMPLES). */
  record: number;
  /**
   * How many of the three narrated fragments are visible. Only meaningful
   * while transcribing; carried on every step so the renderer never has to
   * special-case a phase to know what to draw.
   */
  revealed: number;
  /** Milliseconds to hold this step. */
  ms: number;
}

/**
 * Two records, not three, plus a permanent "…" row saying it keeps going.
 *
 * Twenty seconds of hero animation is longer than anyone watches. Two records
 * carry the whole message — the first teaches the mechanic, the second shows
 * that rows accumulate into the same sheet — and the ellipsis communicates
 * "and so on" for free, in no time at all.
 */
export const RECORD_COUNT = 2;

/**
 * The second record runs ~35% faster. Comprehension is not linear: by the
 * second pass the viewer already knows the mechanic and is only watching the
 * sheet fill, so repeating the teaching pace would cost seconds and add
 * nothing.
 */
const SPEEDS = [1, 0.65];

const BASE = {
  recording: 1800,
  /** Per fragment; three fragments make up the sentence. */
  fragment: 500,
  confirming: 520,
  committed: 620,
} as const;

const REST_MS = 2400;

function scale(ms: number, record: number): number {
  return Math.round(ms * SPEEDS[record]);
}

/** The full loop, as a flat list of steps. */
export function buildTimeline(): Step[] {
  const steps: Step[] = [];

  for (let record = 0; record < RECORD_COUNT; record += 1) {
    steps.push({ phase: 'recording', record, revealed: 0, ms: scale(BASE.recording, record) });

    // Fragments appear one at a time — venue, then capacity, then date — which
    // is what dictation actually looks like and is far more legible than the
    // whole sentence arriving at once.
    for (let revealed = 1; revealed <= 3; revealed += 1) {
      steps.push({
        phase: 'transcribing',
        record,
        revealed,
        ms: scale(BASE.fragment, record),
      });
    }

    steps.push({ phase: 'confirming', record, revealed: 3, ms: scale(BASE.confirming, record) });
    steps.push({ phase: 'committed', record, revealed: 3, ms: scale(BASE.committed, record) });
  }

  steps.push({ phase: 'resting', record: RECORD_COUNT - 1, revealed: 3, ms: REST_MS });
  return steps;
}

export const TIMELINE = buildTimeline();

/** Total loop duration in ms — asserted in the tests so it cannot creep. */
export const LOOP_MS = TIMELINE.reduce((total, step) => total + step.ms, 0);

/**
 * How many rows are filled in at a given step. A row lands when its record
 * reaches `committed`, and stays for the rest of the loop.
 */
export function rowsFilled(step: Step): number {
  if (step.phase === 'resting') return RECORD_COUNT;
  return step.phase === 'committed' ? step.record + 1 : step.record;
}
