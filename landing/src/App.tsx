import { useI18n } from './i18n/LanguageContext';
import type { TranslationKey } from './i18n/translations';
import { LanguageSwitcher } from './components/LanguageSwitcher';
import { IconMic } from './components/Icons';
import { Hero } from './sections/Hero';
import { HowItWorks } from './sections/HowItWorks';
import { Features } from './sections/Features';
import { UseCases } from './sections/UseCases';
import { TechStack } from './sections/TechStack';
import { Contact } from './sections/Contact';
import { Footer } from './sections/Footer';
import styles from './App.module.css';

const NAV: { href: string; key: TranslationKey }[] = [
  { href: '#how', key: 'nav.how' },
  { href: '#features', key: 'nav.features' },
  { href: '#cases', key: 'nav.cases' },
  { href: '#tech', key: 'nav.tech' },
  { href: '#contact', key: 'nav.contact' },
];

export function App() {
  const { t } = useI18n();

  return (
    <>
      <header className={styles.nav}>
        <div className={styles.navInner}>
          <a href="#top" className={styles.brand}>
            <span className={styles.brandMark}>
              <IconMic size={18} />
            </span>
            <span className={styles.brandName}>Voxa</span>
          </a>

          <nav className={styles.navLinks} aria-label="Principal">
            {NAV.map((item) => (
              <a key={item.href} href={item.href}>
                {t(item.key)}
              </a>
            ))}
          </nav>

          <LanguageSwitcher />
        </div>
      </header>

      <main>
        <Hero />
        <HowItWorks />
        <Features />
        <UseCases />
        <TechStack />
        <Contact />
      </main>

      <Footer />
    </>
  );
}
