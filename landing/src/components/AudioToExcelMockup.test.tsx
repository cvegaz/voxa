import { render, screen, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { AudioToExcelMockup } from './AudioToExcelMockup';
import { LanguageProvider } from '../i18n/LanguageContext';
import { TIMELINE, LOOP_MS, RECORD_COUNT } from './mockupTimeline';

function renderMockup() {
  return render(
    <LanguageProvider>
      <AudioToExcelMockup />
    </LanguageProvider>
  );
}

/**
 * Advance the machine to a given step index.
 *
 * Deliberately one step per `act()` rather than one big
 * `advanceTimersByTime(total)`: the next timeout is only armed when React
 * re-renders and re-runs the effect, so a single bulk advance fires one
 * callback and then finds no timer left to run. Stepping is what actually
 * drives the machine.
 */
function advanceToStep(target: number) {
  for (let i = 0; i < target; i += 1) {
    act(() => {
      vi.advanceTimersByTime(TIMELINE[i % TIMELINE.length].ms);
    });
  }
}

/** Index of the first step in a phase. */
function stepOf(phase: string): number {
  return TIMELINE.findIndex((s) => s.phase === phase);
}

function mockMatchMedia(reduced: boolean) {
  vi.stubGlobal(
    'matchMedia',
    vi.fn((query: string) => ({
      matches: reduced && query.includes('reduce'),
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
      onchange: null,
    }))
  );
}

describe('AudioToExcelMockup', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockMatchMedia(false);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('renders as an accessible image with a descriptive label', () => {
    renderMockup();
    const fig = screen.getByRole('img');
    expect(fig).toHaveAttribute('aria-label');
    expect(fig.getAttribute('aria-label')?.length).toBeGreaterThan(0);
  });

  it('starts with an empty sheet — no row before anything is narrated', () => {
    renderMockup();
    expect(screen.queryByText('Estadio Azteca')).toBeNull();
    expect(screen.queryByText('87000')).toBeNull();
  });

  it('reveals the narration one fragment at a time', () => {
    renderMockup();

    // First transcribing step: only the venue has been "heard".
    const first = stepOf('transcribing');
    advanceToStep(first);
    expect(screen.getByText(/Estadio Azteca/)).toBeInTheDocument();
    expect(screen.queryByText(/87 000/)).toBeNull();

    // Two steps later the whole sentence is there.
    advanceToStep(first + 2);
    expect(screen.getByText(/aforo 87 000/)).toBeInTheDocument();
    expect(screen.getByText(/17 de septiembre/)).toBeInTheDocument();
  });

  it('lands the first row only after the record is committed', () => {
    renderMockup();

    const commit = stepOf('committed');
    // The step before committing is `confirming` — still no row.
    advanceToStep(commit - 1);
    expect(screen.queryByText('87000')).toBeNull();

    advanceToStep(commit);
    expect(screen.getByText('Estadio Azteca')).toBeInTheDocument();
    expect(screen.getByText('87000')).toBeInTheDocument();
    expect(screen.getByText('17-sep-2026')).toBeInTheDocument();
  });

  it('accumulates the second row into the same sheet without losing the first', () => {
    renderMockup();

    advanceToStep(stepOf('resting'));

    // Both records present at once — the whole point of the animation.
    expect(screen.getByText('Estadio Azteca')).toBeInTheDocument();
    expect(screen.getByText('Estadio BBVA')).toBeInTheDocument();
    expect(screen.getByText('51000')).toBeInTheDocument();
    // And the ellipsis row says it keeps going beyond the two shown.
    expect(screen.getByText('…')).toBeInTheDocument();
  });

  it('loops back to an empty sheet', () => {
    renderMockup();
    advanceToStep(TIMELINE.length);
    expect(screen.queryByText('87000')).toBeNull();
    expect(screen.queryByText('Estadio BBVA')).toBeNull();
  });

  it('stays under 15 seconds per loop', () => {
    // A hero animation nobody finishes watching communicates only its first
    // few seconds. This guards the budget against future tuning.
    expect(LOOP_MS).toBeLessThan(15_000);
    expect(RECORD_COUNT).toBe(2);
  });
});

describe('AudioToExcelMockup under reduced motion', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockMatchMedia(true);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('shows the finished sheet immediately and never animates', () => {
    renderMockup();

    // No advancing: the end state is there on the first frame.
    expect(screen.getByText('Estadio Azteca')).toBeInTheDocument();
    expect(screen.getByText('Estadio BBVA')).toBeInTheDocument();
    expect(screen.getByText('…')).toBeInTheDocument();

    // And no timer was armed, so the content cannot change under them.
    expect(vi.getTimerCount()).toBe(0);
  });
});
