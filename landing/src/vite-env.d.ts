/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
  readonly VITE_GITHUB_URL?: string;
  readonly VITE_APP_URL?: string;
  readonly VITE_LINKEDIN_URL?: string;
  readonly VITE_CALENDLY_URL?: string;
  readonly VITE_CONTACT_EMAIL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
