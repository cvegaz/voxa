/* eslint-disable react-refresh/only-export-components --
 * This file exports a component (LanguageProvider) alongside non-components
 * (useI18n, localized, getCurrentLanguage), which the rule flags because it
 * coarsens Vite's Fast Refresh granularity in dev.
 *
 * Kept together on purpose. It is the standard React context shape — provider
 * and its hook in one module — and the three exports share the module-level
 * `currentLanguage` mirror that lets non-React code (API error mappers, which
 * run outside the component tree) localize. Splitting them would mean exporting
 * that mutable state across a module boundary: real coupling, added to buy back
 * a dev-server nicety. The warning is acknowledged rather than obeyed.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import {
  DEFAULT_LANGUAGE,
  SUPPORTED_LANGUAGES,
  messages,
  type Language,
  type TranslationKey,
} from './translations';

const STORAGE_KEY = 'voxa.lang';

/** Substitute `{token}` placeholders in a message with the given params. */
function format(template: string, params?: Record<string, string | number>): string {
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (_, key) =>
    key in params ? String(params[key]) : `{${key}}`
  );
}

function translate(
  lang: Language,
  key: TranslationKey,
  params?: Record<string, string | number>
): string {
  // Fall back to the default language, then to the key itself, so a missing
  // translation degrades gracefully instead of rendering blank.
  const template = messages[lang][key] ?? messages[DEFAULT_LANGUAGE][key] ?? key;
  return format(template, params);
}

export interface I18nValue {
  lang: Language;
  setLang: (lang: Language) => void;
  t: (key: TranslationKey, params?: Record<string, string | number>) => string;
}

// Module-level mirror of the active language so non-React code (e.g. API error
// mappers that run outside the component tree) can localize too.
let currentLanguage: Language = DEFAULT_LANGUAGE;
export const getCurrentLanguage = (): Language => currentLanguage;

/**
 * Pick a string by the active language, for code that runs outside the React
 * tree (e.g. API error mappers invoked when an error is constructed). Captures
 * the language active at call time.
 */
export const localized = (es: string, en: string): string =>
  currentLanguage === 'en' ? en : es;

function readStoredLanguage(): Language {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && SUPPORTED_LANGUAGES.includes(stored as Language)) {
      return stored as Language;
    }
  } catch {
    // localStorage may be unavailable (private mode, SSR); fall back to default.
  }
  return DEFAULT_LANGUAGE;
}

// Default context value uses the default language and is fully functional, so a
// component rendered without a provider (e.g. in unit tests) still translates.
const LanguageContext = createContext<I18nValue>({
  lang: DEFAULT_LANGUAGE,
  setLang: () => {},
  t: (key, params) => translate(DEFAULT_LANGUAGE, key, params),
});

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Language>(readStoredLanguage);

  // Keep the module mirror, the persisted value, and <html lang> in sync.
  useEffect(() => {
    currentLanguage = lang;
    try {
      localStorage.setItem(STORAGE_KEY, lang);
    } catch {
      // ignore persistence failures
    }
    document.documentElement.lang = lang;
  }, [lang]);

  const setLang = useCallback((next: Language) => setLangState(next), []);

  const value = useMemo<I18nValue>(
    () => ({
      lang,
      setLang,
      t: (key, params) => translate(lang, key, params),
    }),
    [lang, setLang]
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

/** Access the current language, setter, and the `t()` translator. */
export function useI18n(): I18nValue {
  return useContext(LanguageContext);
}
