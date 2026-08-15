/* eslint-disable react-refresh/only-export-components --
 * Provider and its hook in one module: the standard React context shape. The
 * rule flags it because co-locating them coarsens Fast Refresh granularity in
 * dev — a nicety not worth the coupling a split would introduce. Same decision
 * as the app's LanguageContext, where the reasoning is spelled out in full.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
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
  const template = messages[lang][key] ?? messages[DEFAULT_LANGUAGE][key] ?? key;
  return format(template, params);
}

export interface I18nValue {
  lang: Language;
  setLang: (lang: Language) => void;
  t: (key: TranslationKey, params?: Record<string, string | number>) => string;
}

function readStoredLanguage(): Language {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && SUPPORTED_LANGUAGES.includes(stored as Language)) {
      return stored as Language;
    }
  } catch {
    // localStorage may be unavailable (private mode); fall back to default.
  }
  return DEFAULT_LANGUAGE;
}

// Default context value is fully functional so a component rendered without a
// provider (e.g. in unit tests) still translates.
const LanguageContext = createContext<I18nValue>({
  lang: DEFAULT_LANGUAGE,
  setLang: () => {},
  t: (key, params) => translate(DEFAULT_LANGUAGE, key, params),
});

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Language>(readStoredLanguage);

  useEffect(() => {
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
