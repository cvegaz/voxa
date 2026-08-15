import { useEffect, useRef } from 'react';
import { useI18n } from '../i18n/LanguageContext';
import styles from './PrivacyNotice.module.css';

export interface PrivacyNoticeProps {
  onClose: () => void;
}

/**
 * Privacy notice for the marketing site (ADR-0019 §8).
 *
 * Narrower than the app's, on purpose: the landing collects only what the contact
 * form is given. It still has to exist — a form that takes a name and an email is
 * a personal-data collection point, and in Mexico (LFPDPPP) an *aviso de
 * privacidad* is a legal requirement rather than a courtesy.
 *
 * The demo's own processing (voice, OpenAI, retention) is disclosed inside the
 * app, where it happens; this notice says so and points there instead of copying
 * the text, so the two cannot drift apart.
 */
export function PrivacyNotice({ onClose }: PrivacyNoticeProps) {
  const { t } = useI18n();
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [onClose]);

  const sections = [
    { title: t('privacy.contactTitle'), body: t('privacy.contactBody') },
    { title: t('privacy.demoTitle'), body: t('privacy.demoBody') },
    { title: t('privacy.rightsTitle'), body: t('privacy.rightsBody') },
  ];

  return (
    <div className={styles.backdrop} onClick={onClose} role="presentation">
      <div
        className={styles.dialog}
        role="dialog"
        aria-modal="true"
        aria-labelledby="landing-privacy-title"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id="landing-privacy-title" className={styles.title}>
          {t('privacy.title')}
        </h2>

        {sections.map((section) => (
          <section key={section.title} className={styles.section}>
            <h3 className={styles.sectionTitle}>{section.title}</h3>
            <p className={styles.sectionBody}>{section.body}</p>
          </section>
        ))}

        <button
          ref={closeRef}
          type="button"
          className={styles.close}
          onClick={onClose}
        >
          {t('privacy.close')}
        </button>
      </div>
    </div>
  );
}
