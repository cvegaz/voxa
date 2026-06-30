import { useI18n } from '../i18n/LanguageContext';
import type { TranslationKey } from '../i18n/translations';
import { Section } from '../components/Section';
import styles from './Features.module.css';

const FEATURES: { titleKey: TranslationKey; descKey: TranslationKey }[] = [
  { titleKey: 'features.bilingual.title', descKey: 'features.bilingual.desc' },
  { titleKey: 'features.stateless.title', descKey: 'features.stateless.desc' },
  { titleKey: 'features.cap.title', descKey: 'features.cap.desc' },
  { titleKey: 'features.mic.title', descKey: 'features.mic.desc' },
  { titleKey: 'features.absent.title', descKey: 'features.absent.desc' },
  { titleKey: 'features.dates.title', descKey: 'features.dates.desc' },
];

export function Features() {
  const { t } = useI18n();

  return (
    <Section
      id="features"
      eyebrow={t('nav.features')}
      title={t('features.title')}
      subtitle={t('features.subtitle')}
      tinted
    >
      <div className={styles.grid}>
        {FEATURES.map((feature) => (
          <article key={feature.titleKey} className={styles.card}>
            <h3 className={styles.cardTitle}>{t(feature.titleKey)}</h3>
            <p className={styles.cardDesc}>{t(feature.descKey)}</p>
          </article>
        ))}
      </div>
    </Section>
  );
}
