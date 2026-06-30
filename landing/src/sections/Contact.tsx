import { useState, type FormEvent } from 'react';
import { useI18n } from '../i18n/LanguageContext';
import { Section } from '../components/Section';
import { IconCheck } from '../components/Icons';
import { submitContact } from '../services/contactApi';
import { LINKS } from '../config';
import styles from './Contact.module.css';

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

type Status = 'idle' | 'submitting' | 'success' | 'error';

interface FieldErrors {
  name?: string;
  email?: string;
  message?: string;
}

export function Contact() {
  const { t, lang } = useI18n();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [company, setCompany] = useState('');
  const [message, setMessage] = useState('');
  const [website, setWebsite] = useState(''); // honeypot
  const [errors, setErrors] = useState<FieldErrors>({});
  const [status, setStatus] = useState<Status>('idle');

  function validate(): FieldErrors {
    const next: FieldErrors = {};
    if (!name.trim()) next.name = t('contact.validation.name');
    if (!EMAIL_RE.test(email.trim())) next.email = t('contact.validation.email');
    if (!message.trim()) next.message = t('contact.validation.message');
    return next;
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const found = validate();
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    setStatus('submitting');
    try {
      await submitContact({
        name: name.trim(),
        email: email.trim(),
        company: company.trim() || undefined,
        message: message.trim(),
        sourceLang: lang,
        website,
      });
      setStatus('success');
      setName('');
      setEmail('');
      setCompany('');
      setMessage('');
    } catch {
      setStatus('error');
    }
  }

  if (status === 'success') {
    return (
      <Section id="contact" eyebrow={t('nav.contact')} title={t('contact.title')}>
        <div className={styles.success} role="status">
          <span className={styles.successIcon} aria-hidden="true">
            <IconCheck size={28} />
          </span>
          <p>{t('contact.success')}</p>
        </div>
      </Section>
    );
  }

  return (
    <Section
      id="contact"
      eyebrow={t('nav.contact')}
      title={t('contact.title')}
      subtitle={t('contact.subtitle')}
    >
      <form className={styles.form} onSubmit={handleSubmit} noValidate>
        <div className={styles.row}>
          <div className={styles.field}>
            <label htmlFor="contact-name">{t('contact.name')}</label>
            <input
              id="contact-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t('contact.namePlaceholder')}
              aria-invalid={!!errors.name}
              className={errors.name ? styles.invalid : ''}
            />
            {errors.name && <span className={styles.error}>{errors.name}</span>}
          </div>

          <div className={styles.field}>
            <label htmlFor="contact-email">{t('contact.email')}</label>
            <input
              id="contact-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder={t('contact.emailPlaceholder')}
              aria-invalid={!!errors.email}
              className={errors.email ? styles.invalid : ''}
            />
            {errors.email && <span className={styles.error}>{errors.email}</span>}
          </div>
        </div>

        <div className={styles.field}>
          <label htmlFor="contact-company">
            {t('contact.company')} <span className={styles.optional}>· {t('contact.optional')}</span>
          </label>
          <input
            id="contact-company"
            type="text"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            placeholder={t('contact.companyPlaceholder')}
          />
        </div>

        <div className={styles.field}>
          <label htmlFor="contact-message">{t('contact.message')}</label>
          <textarea
            id="contact-message"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder={t('contact.messagePlaceholder')}
            rows={5}
            aria-invalid={!!errors.message}
            className={errors.message ? styles.invalid : ''}
          />
          {errors.message && <span className={styles.error}>{errors.message}</span>}
        </div>

        {/* Honeypot: hidden from users; only bots fill it. */}
        <div className={styles.honeypot} aria-hidden="true">
          <label htmlFor="contact-website">Website</label>
          <input
            id="contact-website"
            type="text"
            tabIndex={-1}
            autoComplete="off"
            value={website}
            onChange={(e) => setWebsite(e.target.value)}
          />
        </div>

        {status === 'error' && (
          <p className={styles.formError} role="alert">
            {t('contact.error')}
          </p>
        )}

        <div className={styles.actions}>
          <button
            type="submit"
            className="btn btn-primary btn-lg"
            disabled={status === 'submitting'}
          >
            {status === 'submitting' ? t('contact.submitting') : t('contact.submit')}
          </button>

          <div className={styles.alts}>
            {LINKS.email && (
              <a className={styles.altLink} href={`mailto:${LINKS.email}`}>
                {t('contact.altEmail')}
              </a>
            )}
            {LINKS.calendly && (
              <a
                className={styles.altLink}
                href={LINKS.calendly}
                target="_blank"
                rel="noreferrer noopener"
              >
                {t('contact.altCalendly')}
              </a>
            )}
          </div>
        </div>
      </form>
    </Section>
  );
}
