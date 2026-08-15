import { useI18n } from '../i18n/LanguageContext';
import { AudioToExcelMockup } from '../components/AudioToExcelMockup';
import { IconGithub, IconArrowRight, IconExternal } from '../components/Icons';
import { LINKS } from '../config';
import styles from './Hero.module.css';

/**
 * CTA hierarchy: the demo is the primary action, contact is secondary.
 *
 * This is product-led rather than sales-led on purpose. Voxa is hard to
 * describe and obvious to see — "structured data capture by voice" means
 * nothing read, and thirty seconds of narrating means everything. It also
 * makes the funnel instrumentation (ADR-0019 §7) worth having: aha rate,
 * downloads and walls measure nothing if the demo sits behind a ghost button.
 *
 * When no app URL is configured the hierarchy falls back to contact-primary.
 * That is not a nicety — it is the difference between one fewer button and a
 * headline button that goes nowhere.
 */
export function Hero() {
  const { t } = useI18n();
  const hasDemo = Boolean(LINKS.app);

  return (
    <section className={styles.hero} id="top">
      <div className={styles.inner}>
        <div className={styles.copy}>
          <p className={styles.badge}>{t('hero.badge')}</p>
          <h1 className={styles.title}>{t('hero.title')}</h1>
          <p className={styles.subtitle}>{t('hero.subtitle')}</p>

          <div className={styles.ctas}>
            {hasDemo && (
              <a
                href={LINKS.app}
                className="btn btn-primary btn-lg"
                target="_blank"
                rel="noreferrer noopener"
              >
                {t('hero.ctaApp')}
                <IconExternal size={16} />
              </a>
            )}

            {/* Contact stays visible and clear. Demoting it is the point;
                hiding it would trade a qualified lead for a click. */}
            <a
              href="#contact"
              className={`btn btn-lg ${hasDemo ? 'btn-secondary' : 'btn-primary'}`}
            >
              {t('hero.ctaPrimary')}
              <IconArrowRight size={18} />
            </a>

            <a
              href={LINKS.github}
              className="btn btn-ghost btn-lg"
              target="_blank"
              rel="noreferrer noopener"
            >
              <IconGithub size={18} />
              {t('hero.ctaGithub')}
            </a>
          </div>

          {/* Expectation-setting, and the cheapest conversion lever on the
              page: "no sign-up" is what lifts the click, and naming the cap
              here means the wall is not a surprise when a visitor hits it. */}
          {hasDemo && <p className={styles.trialNote}>{t('hero.trialNote')}</p>}
        </div>

        <div className={styles.visual}>
          <AudioToExcelMockup />
        </div>
      </div>
    </section>
  );
}
