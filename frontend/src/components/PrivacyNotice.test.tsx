import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { PrivacyNotice } from './PrivacyNotice';

/**
 * ADR-0019 §8 — the notice is a release blocker, so its *content* is under test,
 * not just that a dialog opens.
 *
 * Each assertion below corresponds to a disclosure the app owes its visitors:
 * that their voice leaves for a third party, that the audio is not kept, that
 * the email is optional, and that column names (but never values) are retained.
 * A notice that stops saying one of these has stopped doing its job, and nothing
 * else in the codebase would notice.
 */
describe('PrivacyNotice', () => {
  it('discloses that the audio is sent to OpenAI', () => {
    render(<PrivacyNotice onClose={() => {}} />);
    expect(screen.getByText(/openai/i)).toBeInTheDocument();
  });

  it('discloses that the audio file itself is not stored', () => {
    render(<PrivacyNotice onClose={() => {}} />);
    expect(screen.getByText(/no se guarda en nuestros servidores/i)).toBeInTheDocument();
  });

  it('discloses that the email is optional and never blocks the download', () => {
    render(<PrivacyNotice onClose={() => {}} />);
    expect(screen.getByText(/opcional y nunca bloquea la descarga/i)).toBeInTheDocument();
  });

  it('discloses the telemetry, including the column-names limit', () => {
    // The distinction that makes retaining the industry signal defensible:
    // names are kept, narrated values never are.
    render(<PrivacyNotice onClose={() => {}} />);
    expect(screen.getByText(/nunca los valores que narras/i)).toBeInTheDocument();
  });

  it('warns that this is a demo and data may be deleted', () => {
    render(<PrivacyNotice onClose={() => {}} />);
    expect(screen.getByText(/no uses voxa para información sensible/i)).toBeInTheDocument();
  });

  it('states the ARCO rights and who the controller is', () => {
    render(<PrivacyNotice onClose={() => {}} />);
    expect(screen.getByText(/derechos arco/i)).toBeInTheDocument();
    expect(screen.getByText(/carlos vega/i)).toBeInTheDocument();
  });
});

describe('PrivacyNotice — accessibility', () => {
  it('is announced as a modal dialog', () => {
    render(<PrivacyNotice onClose={() => {}} />);
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
  });

  it('closes on Escape', () => {
    // A modal that can only be dismissed with a mouse traps keyboard users.
    const onClose = vi.fn();
    render(<PrivacyNotice onClose={onClose} />);

    fireEvent.keyDown(document, { key: 'Escape' });

    expect(onClose).toHaveBeenCalled();
  });

  it('closes on the close button', () => {
    const onClose = vi.fn();
    render(<PrivacyNotice onClose={onClose} />);

    fireEvent.click(screen.getByRole('button', { name: /cerrar/i }));

    expect(onClose).toHaveBeenCalled();
  });

  it('does not close when the dialog body itself is clicked', () => {
    const onClose = vi.fn();
    render(<PrivacyNotice onClose={onClose} />);

    fireEvent.click(screen.getByRole('dialog'));

    expect(onClose).not.toHaveBeenCalled();
  });
});
