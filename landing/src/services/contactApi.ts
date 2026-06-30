import { API_BASE } from '../config';

export interface ContactPayload {
  name: string;
  email: string;
  company?: string;
  message: string;
  sourceLang?: string;
  /** Honeypot — always sent empty by the real form; bots fill it. */
  website?: string;
}

export interface ContactResult {
  id: string | null;
  status: string;
}

/** Error carrying the backend's flattened `{ detail, errorCode }` contract. */
export class ContactApiError extends Error {
  errorCode: string;
  constructor(detail: string, errorCode: string) {
    super(detail);
    this.name = 'ContactApiError';
    this.errorCode = errorCode;
  }
}

/**
 * POST the contact form to the backend. The backend speaks camelCase and
 * returns `{ id, status }` on success or `{ detail, errorCode }` on error.
 */
export async function submitContact(payload: ContactPayload): Promise<ContactResult> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/contact`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  } catch {
    throw new ContactApiError('Network error', 'NETWORK_ERROR');
  }

  let data: unknown = null;
  try {
    data = await response.json();
  } catch {
    // No/invalid JSON body.
  }

  if (!response.ok) {
    const body = (data ?? {}) as { detail?: string; errorCode?: string };
    throw new ContactApiError(body.detail ?? 'Request failed', body.errorCode ?? 'ERROR');
  }

  return data as ContactResult;
}
