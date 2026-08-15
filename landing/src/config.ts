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
  /** Deployed app ("Pruébalo tú mismo"). Hidden when empty. */
  app: env.VITE_APP_URL || '',
  /**
   * playPro Stats in production — the case study's evidence.
   *
   * Points at the app rather than playprosystems.com: the card claims pps was
   * built as a configuration over the Voxa core, and the proof of that is the
   * working product, not its marketing site. Its reads are public, so a
   * visitor sees real games without an account.
   *
   * Unlike the other links this has a real default rather than an empty
   * string: it is a fact about a live third product, not per-deployment
   * config. The env var exists so it can be pointed elsewhere or blanked out
   * (which hides the link) without a code change.
   */
  playpro: env.VITE_PLAYPRO_URL ?? 'https://app.playprosystems.com',
  linkedin: env.VITE_LINKEDIN_URL || '',
  calendly: env.VITE_CALENDLY_URL || '',
  email: env.VITE_CONTACT_EMAIL || '',
} as const;
