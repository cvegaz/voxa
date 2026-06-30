import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, beforeEach } from 'vitest';
import { LanguageSwitcher } from './LanguageSwitcher';
import { LanguageProvider, useI18n } from '../i18n/LanguageContext';

/** Probe that renders the current hero title so we can assert the language. */
function HeroTitleProbe() {
  const { t } = useI18n();
  return <p>{t('hero.title')}</p>;
}

describe('LanguageSwitcher', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('defaults to Spanish and switches the whole UI to English', async () => {
    const user = userEvent.setup();
    render(
      <LanguageProvider>
        <LanguageSwitcher />
        <HeroTitleProbe />
      </LanguageProvider>
    );

    // Default ES
    expect(screen.getByText('Habla, y Voxa llena tu Excel.')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /English/i }));

    expect(screen.getByText('Talk, and Voxa fills your Excel.')).toBeInTheDocument();
    expect(localStorage.getItem('voxa.lang')).toBe('en');
  });
});
