import { useI18n } from '../i18n/LanguageContext';
import { Section } from '../components/Section';
import { IconArrowRight } from '../components/Icons';
import styles from './UseCases.module.css';

export function UseCases() {
  const { t } = useI18n();

  return (
    <Section
      id="cases"
      eyebrow={t('nav.cases')}
      title={t('cases.title')}
      subtitle={t('cases.subtitle')}
    >
      <div className={styles.grid}>
        {/* Real case: playPro Stats */}
        <article className={styles.card}>
          <span className={styles.tag}>{t('cases.playpro.tag')}</span>
          <h3 className={styles.cardTitle}>{t('cases.playpro.title')}</h3>
          <p className={styles.cardDesc}>{t('cases.playpro.desc')}</p>
        </article>

        {/* Invitation: your domain → the hook */}
        <article className={`${styles.card} ${styles.cardAccent}`}>
          <span className={`${styles.tag} ${styles.tagAccent}`}>{t('cases.yours.tag')}</span>
          <h3 className={styles.cardTitle}>{t('cases.yours.title')}</h3>
          <p className={styles.cardDesc}>{t('cases.yours.desc')}</p>
          <a href="#contact" className="btn btn-primary">
            {t('cases.yours.cta')}
            <IconArrowRight size={18} />
          </a>
        </article>
      </div>
    </Section>
  );
}
