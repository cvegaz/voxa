import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { SessionControls } from './SessionControls';

describe('SessionControls', () => {
  const defaultProps = {
    totalRows: 2,
    maxRows: 5,
    finalized: false,
    isBusy: false,
    onFinalize: vi.fn(),
    onDownload: vi.fn(),
  };

  it('shows the capture counter', () => {
    render(<SessionControls {...defaultProps} />);
    expect(screen.getByText('2 / 5 registros')).toBeInTheDocument();
  });

  it('shows "Finalizar" while open and "Descargar" only once finalized', () => {
    const { rerender } = render(<SessionControls {...defaultProps} />);
    expect(
      screen.getByRole('button', { name: /finalizar la sesión/i })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /descargar el archivo/i })
    ).not.toBeInTheDocument();

    rerender(<SessionControls {...defaultProps} finalized={true} />);
    expect(
      screen.getByRole('button', { name: /descargar el archivo/i })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /finalizar la sesión/i })
    ).not.toBeInTheDocument();
  });

  it('disables "Finalizar" when there are no records yet', () => {
    render(<SessionControls {...defaultProps} totalRows={0} />);
    expect(screen.getByRole('button', { name: /finalizar/i })).toHaveAttribute(
      'aria-disabled',
      'true'
    );
  });

  it('calls onFinalize when the finalize button is clicked', () => {
    const onFinalize = vi.fn();
    render(<SessionControls {...defaultProps} onFinalize={onFinalize} />);
    fireEvent.click(screen.getByRole('button', { name: /finalizar/i }));
    expect(onFinalize).toHaveBeenCalledTimes(1);
  });

  it('calls onDownload when the download button is clicked', () => {
    const onDownload = vi.fn();
    render(<SessionControls {...defaultProps} finalized={true} onDownload={onDownload} />);
    fireEvent.click(screen.getByRole('button', { name: /descargar/i }));
    expect(onDownload).toHaveBeenCalledTimes(1);
  });

  it('shows the cap message when finalized by reaching the limit', () => {
    render(<SessionControls {...defaultProps} totalRows={5} finalized={true} />);
    expect(screen.getByText(/límite de 5 registros alcanzado/i)).toBeInTheDocument();
  });

  it('shows a plain finalized message when closed below the cap', () => {
    render(<SessionControls {...defaultProps} totalRows={2} finalized={true} />);
    expect(screen.getByText(/sesión finalizada/i)).toBeInTheDocument();
  });

  it('disables actions while a request is in flight', () => {
    const { rerender } = render(<SessionControls {...defaultProps} isBusy={true} />);
    expect(screen.getByRole('button', { name: /finalizar/i })).toHaveAttribute(
      'aria-disabled',
      'true'
    );

    rerender(<SessionControls {...defaultProps} finalized={true} isBusy={true} />);
    expect(screen.getByRole('button', { name: /descargar/i })).toHaveAttribute(
      'aria-disabled',
      'true'
    );
  });
});
