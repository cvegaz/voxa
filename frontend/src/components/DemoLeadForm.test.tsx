import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import type { MockInstance } from 'vitest';
import { DemoLeadForm } from './DemoLeadForm';
import { SessionControls } from './SessionControls';
import * as demoLeadApi from '../services/demoLeadApi';

/**
 * The soft gate (ADR-0019 §5).
 *
 * These tests exist mostly to stop the form being "improved" into a wall. Making
 * the field required, gating the download on it, or granting a little quota for
 * filling it are all natural-sounding changes that each break the design.
 */
describe('DemoLeadForm', () => {
  // Typed to the real signature — `ReturnType<typeof vi.spyOn>` widens to an
  // unknown-args mock, which then refuses the concrete spy assigned below.
  let submitSpy: MockInstance<(input: demoLeadApi.DemoLeadInput) => Promise<boolean>>;

  beforeEach(() => {
    submitSpy = vi.spyOn(demoLeadApi, 'submitDemoLead').mockResolvedValue(true);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('asks with a different prompt at each capture point', () => {
    const { rerender } = render(<DemoLeadForm capturePoint="download" />);
    expect(screen.getByText(/te sirvió/i)).toBeInTheDocument();

    rerender(<DemoLeadForm capturePoint="wall" />);
    expect(screen.getByText(/necesitas más registros/i)).toBeInTheDocument();
  });

  it('submits the address with its capture point and session', async () => {
    render(<DemoLeadForm capturePoint="wall" sessionId="session-123" />);

    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: 'alguien@ejemplo.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: /enviar/i }));

    await waitFor(() =>
      expect(submitSpy).toHaveBeenCalledWith({
        email: 'alguien@ejemplo.com',
        capturePoint: 'wall',
        sessionId: 'session-123',
        sourceLang: 'es',
      })
    );
  });

  it('cannot be submitted empty', () => {
    render(<DemoLeadForm capturePoint="download" />);

    expect(screen.getByRole('button', { name: /enviar/i })).toBeDisabled();

    fireEvent.click(screen.getByRole('button', { name: /enviar/i }));
    expect(submitSpy).not.toHaveBeenCalled();
  });

  it('thanks the visitor even when the backend rejected the lead', async () => {
    // A failure here is OUR problem, not the visitor's. Surfacing an error next
    // to the file they just earned would trade something valuable (their sense
    // that this worked) for something optional (our lead).
    submitSpy.mockResolvedValue(false);
    render(<DemoLeadForm capturePoint="download" />);

    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: 'alguien@ejemplo.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: /enviar/i }));

    expect(await screen.findByText(/gracias/i)).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('states what the address is used for', () => {
    // Storing an email next to voice makes the data identifiable; saying so at
    // the point of collection is the minimum, and the privacy notice (Phase 8)
    // is the rest.
    render(<DemoLeadForm capturePoint="download" />);
    expect(screen.getByText(/solo lo usamos para contactarte/i)).toBeInTheDocument();
  });
});

describe('DemoLeadForm — never blocks the download', () => {
  const closedSession = (totalRows: number, maxRows: number) =>
    render(
      <SessionControls
        totalRows={totalRows}
        maxRows={maxRows}
        finalized={true}
        isBusy={false}
        onFinalize={() => {}}
        onDownload={() => {}}
      />
    );

  it('sits after the download button, not in front of it', () => {
    closedSession(3, 3);

    const download = screen.getByRole('button', { name: /descargar el archivo/i });
    const emailField = screen.getByRole('textbox');

    // The download must be reachable and enabled with the field left empty.
    expect(download).not.toHaveAttribute('aria-disabled', 'true');
    expect(emailField).toHaveValue('');
    // DOCUMENT_POSITION_FOLLOWING === 4: the form comes after the download.
    expect(download.compareDocumentPosition(emailField)).toBe(4);
  });

  it('shows the higher-intent prompt when the trial cap closed the session', () => {
    closedSession(3, 3);
    expect(screen.getByText(/necesitas más registros/i)).toBeInTheDocument();
  });

  it('shows the satisfied prompt when the user finalized early', () => {
    closedSession(1, 3);
    expect(screen.getByText(/te sirvió/i)).toBeInTheDocument();
  });
});
