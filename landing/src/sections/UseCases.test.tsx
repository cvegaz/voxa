import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';

/**
 * The playPro Stats card is the landing's only third-party proof: it claims
 * Voxa's core carries a real product with a paying client. A claim like that
 * has to be checkable, so the link is part of the content, not decoration —
 * and a dead or missing one costs more credibility than the claim buys.
 */
async function renderWith(playpro: string | undefined) {
  vi.resetModules();
  vi.doMock('../config', () => ({
    API_BASE: '',
    LINKS: {
      github: 'https://github.com/cvegaz/voxa',
      app: '',
      linkedin: '',
      calendly: '',
      email: '',
      playpro: playpro ?? 'https://app.playprosystems.com',
    },
  }));
  const { UseCases } = await import('./UseCases');
  render(<UseCases />);
}

describe('UseCases — playPro Stats case study', () => {
  afterEach(() => vi.doUnmock('../config'));

  it('links to the live product by default', async () => {
    await renderWith(undefined);

    const link = screen.getByRole('link', { name: /verlo en producción/i });
    expect(link).toHaveAttribute('href', 'https://app.playprosystems.com');
    expect(link).toHaveAttribute('target', '_blank');
    expect(link.getAttribute('rel')).toMatch(/noopener/);
  });

  it('hides the link when explicitly blanked', async () => {
    // An empty value is a deliberate "hide it", not a missing config — see the
    // `??` in config.ts and the commented-out line in .env.example.
    await renderWith('');

    expect(screen.queryByRole('link', { name: /verlo en producción/i })).toBeNull();
    // The card itself stays: the case study is worth telling without the link.
    expect(screen.getByRole('heading', { name: /playpro stats/i })).toBeInTheDocument();
  });
});
