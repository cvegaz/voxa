import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { AudioToExcelMockup } from './AudioToExcelMockup';
import { LanguageProvider } from '../i18n/LanguageContext';

describe('AudioToExcelMockup', () => {
  it('renders as an accessible image with a descriptive label', () => {
    render(
      <LanguageProvider>
        <AudioToExcelMockup />
      </LanguageProvider>
    );
    const fig = screen.getByRole('img');
    expect(fig).toHaveAttribute('aria-label');
    expect(fig.getAttribute('aria-label')?.length).toBeGreaterThan(0);
  });

  it('shows the example Excel row values', () => {
    render(
      <LanguageProvider>
        <AudioToExcelMockup />
      </LanguageProvider>
    );
    expect(screen.getByText('Estadio Azteca')).toBeInTheDocument();
    expect(screen.getByText('87000')).toBeInTheDocument();
    expect(screen.getByText('17-sep-2026')).toBeInTheDocument();
  });
});
