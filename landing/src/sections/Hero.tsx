import { useI18n } from '../i18n/LanguageContext';
import { AudioToExcelMockup } from '../components/AudioToExcelMockup';
import { IconGithub, IconArrowRight, IconExternal } from '../components/Icons';
import { LINKS } from '../config';
import styles from './Hero.module.css';

export function Hero() {
  const { t } = useI18n();

  return (
    <section className={styles.hero} id="top">
      <div className={styles.inner}>
        <div className={styles.copy}>
          <p className={styles.badge}>{t('hero.badge')}</p>
          <h1 className={styles.title}>{t('hero.title')}</h1>
          <p className={styles.subtitle}>{t('hero.subtitle')}</p>

          <div className={styles.ctas}>
            <a href="#contact" className="btn btn-primary btn-lg">
              {t('hero.ctaPrimary')}
              <IconArrowRight size={18} />
            </a>
            <a
              href={LINKS.github}
              className="btn btn-secondary btn-lg"
              target="_blank"
              rel="noreferrer noopener"
            >
              <IconGithub size={18} />
              {t('hero.ctaGithub')}
            </a>
            {LINKS.app && (
              <a
                href={LINKS.app}
                className="btn btn-ghost btn-lg"
                target="_blank"
                rel="noreferrer noopener"
              >
                {t('hero.ctaApp')}
                <IconExternal size={16} />
              </a>
            )}
          </div>
        </div>

        <div className={styles.visual}>
          <AudioToExcelMockup />
        </div>
      </div>
    </section>
  );
}
