import { useEffect, useRef } from 'react';
import { useI18n } from '../i18n/LanguageContext';
import styles from './PrivacyNotice.module.css';

export interface PrivacyNoticeProps {
  onClose: () => void;
}

/**
 * The privacy notice (ADR-0019 §8) — a **release blocker**, not a nicety.
 *
 * Voxa processes voice, which is personal data on its own. Once the demo also
 * stores an email (the soft gate, §5) and per-session telemetry (§7), the two
 * become linkable and the whole set is identifiable. Saying plainly what is
 * collected, where it goes, and how long it stays is the minimum obligation —
 * and in Mexico (LFPDPPP) an *aviso de privacidad* is a legal requirement, not a
 * best practice.
 *
 * Rendered as a dialog rather than a route because the app has no router, and a
 * dialog is reachable from every step of the flow — including the one where the
 * microphone is about to be used, which is the step that matters most.
 */
export function PrivacyNotice({ onClose }: PrivacyNoticeProps) {
  const { t } = useI18n();
  const closeRef = useRef<HTMLButtonElement>(null);

  // Escape closes, and focus lands on the close button: a modal that traps a
  // keyboard user is worse than no modal.
  useEffect(() => {
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [onClose]);

  const sections = [
    { title: t('privacy.audioTitle'), body: t('privacy.audioBody') },
    { title: t('privacy.emailTitle'), body: t('privacy.emailBody') },
    { title: t('privacy.usageTitle'), body: t('privacy.usageBody') },
    { title: t('privacy.retentionTitle'), body: t('privacy.retentionBody') },
    { title: t('privacy.rightsTitle'), body: t('privacy.rightsBody') },
  ];

  return (
    <div
      className={styles.backdrop}
      onClick={onClose}
      role="presentation"
    >
      <div
        className={styles.dialog}
        role="dialog"
        aria-modal="true"
        aria-labelledby="privacy-title"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id="privacy-title" className={styles.title}>
          {t('privacy.title')}
        </h2>
        <p className={styles.intro}>{t('privacy.intro')}</p>

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
