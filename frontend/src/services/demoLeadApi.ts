/**
 * Client for the demo lead soft gate (ADR-0019 §5).
 *
 * Deliberately fire-and-forget from the caller's point of view: this call must
 * never be able to block, delay, or fail the thing the user actually came for
 * (their .xlsx). The gate is soft — see `submitDemoLead`.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';

/** Short on purpose: nobody should wait on a lead submission. */
const LEAD_TIMEOUT_MS = 8_000;

export type CapturePoint = 'download' | 'wall';

export interface DemoLeadInput {
  email: string;
  capturePoint: CapturePoint;
  sessionId?: string;
  sourceLang?: string;
}

/**
 * Record an email volunteered from inside the demo.
 *
 * Returns `true` when the backend accepted it, `false` on any failure — and
 * **never throws**. That is the point: a lead is a nice-to-have for us, while the
 * download is the whole reason the visitor is here. Letting a failed marketing
 * call surface as an error next to their file would trade something valuable for
 * something optional.
 */
export async function submitDemoLead(input: DemoLeadInput): Promise<boolean> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), LEAD_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE_URL}/demo-leads`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: input.email,
        capturePoint: input.capturePoint,
        sessionId: input.sessionId,
        sourceLang: input.sourceLang,
      }),
      signal: controller.signal,
    });
    return response.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(timeout);
  }
}
