import { useState } from 'react';
import { useI18n } from '../i18n/LanguageContext';
import { submitDemoLead, type CapturePoint } from '../services/demoLeadApi';
import styles from './DemoLeadForm.module.css';

export interface DemoLeadFormProps {
  /** Which moment this is: finishing a capture, or hitting the trial wall. */
  capturePoint: CapturePoint;
  /** Session the lead came from, when there is one. */
  sessionId?: string;
}

/**
 * The soft gate (ADR-0019 §5): an optional email field shown at the two moments
 * of demonstrated interest.
 *
 * Three properties define it, and all three are easy to "improve" away:
 *
 * 1. **It never blocks.** It sits BESIDE the download, never in front of it. The
 *    visitor came for their file; charging a toll before handing it over trades a
 *    conversion for a maybe-lead.
 * 2. **It grants nothing.** No extra quota, no unlock. An unverified address that
 *    buys something is a Sybil hole — type a new one, get more.
 * 3. **It cannot fail loudly.** A backend problem here is our problem, not the
 *    visitor's; the form thanks them either way rather than putting an error next
 *    to the file they just earned.
 */
export function DemoLeadForm({ capturePoint, sessionId }: DemoLeadFormProps) {
  const { t, lang } = useI18n();
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'sending' | 'done'>('idle');

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!email.trim() || status === 'sending') return;

    setStatus('sending');
    await submitDemoLead({
      email: email.trim(),
      capturePoint,
      sessionId,
      sourceLang: lang,
    });
    // Resolved the same way whether or not it was accepted — see property 3.
    setStatus('done');
  };

  if (status === 'done') {
    return (
      <p className={styles.thanks} role="status">
        {t('lead.thanks')}
      </p>
    );
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit} noValidate>
      <label className={styles.prompt} htmlFor="demo-lead-email">
        {capturePoint === 'wall' ? t('lead.promptWall') : t('lead.promptDownload')}
      </label>
      <div className={styles.row}>
        <input
          id="demo-lead-email"
          className={styles.input}
          type="email"
          inputMode="email"
          autoComplete="email"
          placeholder={t('lead.placeholder')}
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <button
          type="submit"
          className={styles.submit}
          disabled={!email.trim() || status === 'sending'}
        >
          {t('lead.submit')}
        </button>
      </div>
      <p className={styles.privacy}>{t('lead.privacy')}</p>
    </form>
  );
}
