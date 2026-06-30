/**
 * Landing-page configuration: external links and the backend base URL.
 *
 * All values come from Vite env vars (VITE_*), with safe fallbacks. Edit
 * landing/.env (see .env.example) to point these at your real GitHub repo,
 * deployed app, LinkedIn, Calendly, and contact email.
 */

const env = import.meta.env;

/** Base URL for API calls. Empty in dev → relative `/api/...` via the Vite proxy. */
export const API_BASE = env.VITE_API_BASE ?? '';

export const LINKS = {
  github: env.VITE_GITHUB_URL || 'https://github.com/tu-usuario/voxa',
  /** Deployed app ("Probar la app"). Hidden when empty. */
  app: env.VITE_APP_URL || '',
  linkedin: env.VITE_LINKEDIN_URL || '',
  calendly: env.VITE_CALENDLY_URL || '',
  email: env.VITE_CONTACT_EMAIL || '',
} as const;
