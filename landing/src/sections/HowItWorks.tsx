import { useI18n } from '../i18n/LanguageContext';
import type { TranslationKey } from '../i18n/translations';
import { Section } from '../components/Section';
import styles from './HowItWorks.module.css';

const STEPS: { titleKey: TranslationKey; descKey: TranslationKey }[] = [
  { titleKey: 'how.step1.title', descKey: 'how.step1.desc' },
  { titleKey: 'how.step2.title', descKey: 'how.step2.desc' },
  { titleKey: 'how.step3.title', descKey: 'how.step3.desc' },
  { titleKey: 'how.step4.title', descKey: 'how.step4.desc' },
  { titleKey: 'how.step5.title', descKey: 'how.step5.desc' },
  { titleKey: 'how.step6.title', descKey: 'how.step6.desc' },
];

export function HowItWorks() {
  const { t } = useI18n();

  return (
    <Section id="how" eyebrow={t('nav.how')} title={t('how.title')} subtitle={t('how.subtitle')}>
      <ol className={styles.grid}>
        {STEPS.map((step, i) => (
          <li key={step.titleKey} className={styles.step}>
            <span className={styles.num} aria-hidden="true">
              {i + 1}
            </span>
            <div>
              <h3 className={styles.stepTitle}>{t(step.titleKey)}</h3>
              <p className={styles.stepDesc}>{t(step.descKey)}</p>
            </div>
          </li>
        ))}
      </ol>
    </Section>
  );
}
