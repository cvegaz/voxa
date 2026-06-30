import { useI18n } from '../i18n/LanguageContext';
import { IconMic, IconCheck } from './Icons';
import styles from './AudioToExcelMockup.module.css';

// Bar heights (%) for the faux waveform. Static markup; CSS animates them.
const BARS = [40, 70, 30, 90, 55, 75, 35, 85, 50, 65, 45, 80];

/**
 * Animated, CSS-only illustration of the Voxa flow for the hero: a microphone
 * waveform → a transcribed sentence → a filled Excel row. No video to record;
 * the whole thing loops with pure CSS and freezes under reduced-motion.
 */
export function AudioToExcelMockup() {
  const { t } = useI18n();

  return (
    <div className={styles.mockup} role="img" aria-label={t('mockup.ariaLabel')}>
      {/* 1. Voice capture */}
      <div className={`${styles.card} ${styles.voice}`}>
        <span className={styles.badge}>
          <span className={styles.recDot} aria-hidden="true" />
          {t('mockup.recording')}
        </span>
        <span className={styles.micIcon} aria-hidden="true">
          <IconMic size={18} />
        </span>
        <div className={styles.wave} aria-hidden="true">
          {BARS.map((h, i) => (
            <span
              key={i}
              className={styles.bar}
              style={{ height: `${h}%`, animationDelay: `${i * 0.08}s` }}
            />
          ))}
        </div>
      </div>

      <div className={styles.connector} aria-hidden="true" />

      {/* 2. Transcript */}
      <div className={`${styles.card} ${styles.transcript}`}>
        <span className={styles.badge}>{t('mockup.transcribing')}</span>
        <p className={styles.spoken}>{t('mockup.spoken')}</p>
      </div>

      <div className={styles.connector} aria-hidden="true" />

      {/* 3. Excel row */}
      <div className={`${styles.card} ${styles.sheet}`}>
        <span className={`${styles.badge} ${styles.badgeDone}`}>
          <IconCheck size={14} />
          {t('mockup.done')}
        </span>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>{t('mockup.colVenue')}</th>
              <th>{t('mockup.colCapacity')}</th>
              <th>{t('mockup.colDate')}</th>
            </tr>
          </thead>
          <tbody>
            <tr className={styles.filledRow}>
              <td>Estadio Azteca</td>
              <td>87000</td>
              <td>17-sep-2026</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
