import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import { LanguageSwitcher } from './LanguageSwitcher';
import { LanguageProvider, useI18n } from '../i18n/LanguageContext';
import { messages } from '../i18n/translations';

/** Small consumer to observe the active translation while toggling languages. */
function Probe() {
  const { t } = useI18n();
  return <span data-testid="probe">{t('schema.confirm')}</span>;
}

function renderSwitcher() {
  return render(
    <LanguageProvider>
      <LanguageSwitcher />
      <Probe />
    </LanguageProvider>
  );
}

describe('LanguageSwitcher', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('renders ES and EN options with Spanish active by default', () => {
    renderSwitcher();

    const es = screen.getByRole('button', { name: 'Usar Voxa en español' });
    const en = screen.getByRole('button', { name: 'Use Voxa in English' });

    expect(es).toHaveTextContent('ES');
    expect(en).toHaveTextContent('EN');
    expect(es).toHaveAttribute('aria-pressed', 'true');
    expect(en).toHaveAttribute('aria-pressed', 'false');
  });

  it('exposes a tooltip via the title attribute', () => {
    renderSwitcher();
    expect(
      screen.getByRole('button', { name: 'Use Voxa in English' })
    ).toHaveAttribute('title', 'Use Voxa in English');
  });

  it('switches the active language and re-translates the UI on click', () => {
    renderSwitcher();
    expect(screen.getByTestId('probe')).toHaveTextContent('Confirmar');

    fireEvent.click(screen.getByRole('button', { name: 'Use Voxa in English' }));

    expect(screen.getByTestId('probe')).toHaveTextContent('Confirm');
    expect(
      screen.getByRole('button', { name: 'Use Voxa in English' })
    ).toHaveAttribute('aria-pressed', 'true');
    expect(
      screen.getByRole('button', { name: 'Usar Voxa en español' })
    ).toHaveAttribute('aria-pressed', 'false');
  });

  it('persists the selected language across remounts', () => {
    const { unmount } = renderSwitcher();
    fireEvent.click(screen.getByRole('button', { name: 'Use Voxa in English' }));
    unmount();

    renderSwitcher();
    expect(screen.getByTestId('probe')).toHaveTextContent('Confirm');
  });
});

describe('translation catalog', () => {
  it('has the exact same key set for every language', () => {
    const esKeys = Object.keys(messages.es).sort();
    const enKeys = Object.keys(messages.en).sort();
    expect(enKeys).toEqual(esKeys);
  });
});
