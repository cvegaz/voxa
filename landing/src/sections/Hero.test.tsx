import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Hero } from './Hero';

/**
 * The hero's CTA hierarchy is a product decision, not styling, so it is worth
 * a test: the demo is the primary action and contact is secondary.
 *
 * The reasoning (recorded with the Track 4 work): Voxa is hard to describe and
 * obvious to see. "Structured data capture by voice" means nothing read; thirty
 * seconds of narrating and watching rows appear means everything. When the gap
 * between reading and understanding is that wide, showing beats telling — and
 * the whole funnel instrumentation measures nothing if nobody reaches the demo.
 *
 * LINKS is read at module load from import.meta.env, so each test re-imports
 * the module with a mocked config.
 */

async function renderHeroWith(app: string) {
  vi.resetModules();
  vi.doMock('../config', () => ({
    API_BASE: '',
    LINKS: {
      github: 'https://github.com/cvegaz/voxa',
      app,
      linkedin: '',
      calendly: '',
      email: '',
    },
  }));
  const { Hero: Fresh } = await import('./Hero');
  render(<Fresh />);
}

describe('Hero CTAs', () => {
  beforeEach(() => vi.resetModules());
  afterEach(() => vi.doUnmock('../config'));

  it('makes the demo the primary action when the app URL is configured', async () => {
    await renderHeroWith('https://app.tryvoxa.com');

    const demo = screen.getByRole('link', { name: /pruébalo tú mismo/i });
    expect(demo).toHaveAttribute('href', 'https://app.tryvoxa.com');
    expect(demo.className).toMatch(/btn-primary/);

    // Contact survives as a clear secondary — the demo replaces it as the
    // headline action, it does not remove the way to reach a human.
    const contact = screen.getByRole('link', { name: /hablemos de tu caso/i });
    expect(contact).toHaveAttribute('href', '#contact');
    expect(contact.className).toMatch(/btn-secondary/);
  });

  it('states the trial terms next to the demo CTA', async () => {
    await renderHeroWith('https://app.tryvoxa.com');

    // Expectation-setting, not decoration: "no sign-up" is what lifts the
    // click, and naming the cap up front means the wall is not a surprise
    // when a visitor reaches it.
    expect(screen.getByText(/sin registro/i)).toBeInTheDocument();
    expect(screen.getByText(/3 narraciones/i)).toBeInTheDocument();
  });

  it('falls back to contact as primary when no app URL is configured', async () => {
    // Local development without landing/.env, and any deploy before the app is
    // live. A primary button pointing nowhere is worse than one fewer button.
    await renderHeroWith('');

    expect(screen.queryByRole('link', { name: /pruébalo tú mismo/i })).toBeNull();
    expect(screen.queryByText(/sin registro/i)).toBeNull();

    const contact = screen.getByRole('link', { name: /hablemos de tu caso/i });
    expect(contact.className).toMatch(/btn-primary/);
  });

  it('opens the demo in a new tab without leaking the referrer opener', async () => {
    await renderHeroWith('https://app.tryvoxa.com');

    const demo = screen.getByRole('link', { name: /pruébalo tú mismo/i });
    expect(demo).toHaveAttribute('target', '_blank');
    // rel=noopener is what stops the opened page from reaching back into
    // window.opener; it is a security attribute, not a formality.
    expect(demo.getAttribute('rel')).toMatch(/noopener/);
  });
});

describe('Hero content', () => {
  it('renders the headline', () => {
    render(<Hero />);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/Voxa/);
  });
});
