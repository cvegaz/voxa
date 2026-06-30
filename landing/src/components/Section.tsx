import type { ReactNode } from 'react';
import styles from './Section.module.css';

interface SectionProps {
  id: string;
  /** Eyebrow label above the heading (optional). */
  eyebrow?: string;
  title?: string;
  subtitle?: string;
  /** Tints the section background to alternate rhythm down the page. */
  tinted?: boolean;
  children: ReactNode;
}

/** Standard page section: centered, max-width content with an optional header. */
export function Section({ id, eyebrow, title, subtitle, tinted, children }: SectionProps) {
  return (
    <section
      id={id}
      className={`${styles.section} ${tinted ? styles.tinted : ''}`}
      aria-labelledby={title ? `${id}-title` : undefined}
    >
      <div className={styles.inner}>
        {(eyebrow || title || subtitle) && (
          <header className={styles.header}>
            {eyebrow && <p className={styles.eyebrow}>{eyebrow}</p>}
            {title && (
              <h2 id={`${id}-title`} className={styles.title}>
                {title}
              </h2>
            )}
            {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
          </header>
        )}
        {children}
      </div>
    </section>
  );
}
