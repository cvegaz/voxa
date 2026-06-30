import { useI18n } from '../i18n/LanguageContext';
import type { Language } from '../i18n/translations';
import styles from './LanguageSwitcher.module.css';

interface Option {
  code: Language;
  label: string;
  /** Tooltip/aria text describing the target language (written in that language). */
  titleKey: 'lang.switchToEs' | 'lang.switchToEn';
}

const OPTIONS: Option[] = [
  { code: 'es', label: 'ES', titleKey: 'lang.switchToEs' },
  { code: 'en', label: 'EN', titleKey: 'lang.switchToEn' },
];

/**
 * Top-right language switcher: two pills (ES / EN). The active language is
 * shaded; hovering a pill shows a tooltip ("Usar Voxa en español" /
 * "Use Voxa in English"). Selecting one switches the whole UI and the
 * expected input language for transcription.
 */
export function LanguageSwitcher() {
  const { lang, setLang, t } = useI18n();

  return (
    <div className={styles.container} role="group" aria-label={t('lang.groupLabel')}>
      {OPTIONS.map((option) => {
        const isActive = lang === option.code;
        const title = t(option.titleKey);
        return (
          <button
            key={option.code}
            type="button"
            className={`${styles.pill} ${isActive ? styles.active : ''}`}
            onClick={() => setLang(option.code)}
            aria-pressed={isActive}
            title={title}
            aria-label={title}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
