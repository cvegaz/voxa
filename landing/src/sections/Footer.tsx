import { useState } from 'react';
import { useI18n } from '../i18n/LanguageContext';
import { IconMic } from '../components/Icons';
import { PrivacyNotice } from '../components/PrivacyNotice';
import { LINKS } from '../config';
import styles from './Footer.module.css';

export function Footer() {
  const { t } = useI18n();
  const [showPrivacy, setShowPrivacy] = useState(false);

  return (
    <footer className={styles.footer}>
      <div className={styles.inner}>
        <div className={styles.brandCol}>
          <div className={styles.brand}>
            <span className={styles.mark}>
              <IconMic size={18} />
            </span>
            <span className={styles.name}>Voxa</span>
          </div>
          <p className={styles.tagline}>{t('footer.tagline')}</p>
        </div>

        <nav className={styles.links} aria-label="Footer">
          <a href={LINKS.github} target="_blank" rel="noreferrer noopener">
            {t('footer.github')}
          </a>
          {LINKS.app && (
            <a href={LINKS.app} target="_blank" rel="noreferrer noopener">
              {t('footer.app')}
            </a>
          )}
          {LINKS.linkedin && (
            <a href={LINKS.linkedin} target="_blank" rel="noreferrer noopener">
              {t('footer.linkedin')}
            </a>
          )}
          {/* A button, not an anchor: it opens a dialog rather than navigating,
              and an <a href="#"> would misdescribe that to assistive tech. */}
          <button
            type="button"
            className={styles.privacyLink}
            onClick={() => setShowPrivacy(true)}
          >
            {t('privacy.link')}
          </button>
        </nav>
      </div>

      <p className={styles.rights}>{t('footer.rights')}</p>

      {showPrivacy && <PrivacyNotice onClose={() => setShowPrivacy(false)} />}
    </footer>
  );
}
