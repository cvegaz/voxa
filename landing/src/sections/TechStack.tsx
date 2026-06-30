import { useI18n } from '../i18n/LanguageContext';
import type { TranslationKey } from '../i18n/translations';
import { Section } from '../components/Section';
import { IconGithub } from '../components/Icons';
import { LINKS } from '../config';
import styles from './TechStack.module.css';

const LAYERS: { labelKey: TranslationKey; valueKey: TranslationKey }[] = [
  { labelKey: 'tech.layer.frontend', valueKey: 'tech.val.frontend' },
  { labelKey: 'tech.layer.backend', valueKey: 'tech.val.backend' },
  { labelKey: 'tech.layer.db', valueKey: 'tech.val.db' },
  { labelKey: 'tech.layer.ai', valueKey: 'tech.val.ai' },
  { labelKey: 'tech.layer.infra', valueKey: 'tech.val.infra' },
];

const QUALITY: TranslationKey[] = [
  'tech.quality.tests',
  'tech.quality.adr',
  'tech.quality.layers',
];

export function TechStack() {
  const { t } = useI18n();

  return (
    <Section
      id="tech"
      eyebrow={t('nav.tech')}
      title={t('tech.title')}
      subtitle={t('tech.subtitle')}
      tinted
    >
      <div className={styles.layout}>
        <dl className={styles.stack}>
          {LAYERS.map((layer) => (
            <div key={layer.labelKey} className={styles.row}>
              <dt className={styles.label}>{t(layer.labelKey)}</dt>
              <dd className={styles.value}>{t(layer.valueKey)}</dd>
            </div>
          ))}
        </dl>

        <div className={styles.side}>
          <ul className={styles.quality}>
            {QUALITY.map((key) => (
              <li key={key} className={styles.qualityItem}>
                {t(key)}
              </li>
            ))}
          </ul>
          <a
            href={LINKS.github}
            className="btn btn-secondary"
            target="_blank"
            rel="noreferrer noopener"
          >
            <IconGithub size={18} />
            {t('tech.repoCta')}
          </a>
        </div>
      </div>
    </Section>
  );
}
