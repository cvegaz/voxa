import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ControlButtons } from './ControlButtons';

describe('ControlButtons', () => {
  const defaultProps = {
    transcribedText: 'Texto de prueba',
    hasConfirmedSchema: true,
    isLLMProcessing: false,
    onAccept: vi.fn(),
    onReset: vi.fn(),
  };

  it('renders both buttons', () => {
    render(<ControlButtons {...defaultProps} />);

    expect(screen.getByRole('button', { name: /aceptar/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /agregar nuevo/i })).toBeInTheDocument();
  });

  it('"Aceptar" is enabled when text is non-empty and schema is confirmed', () => {
    render(<ControlButtons {...defaultProps} />);

    const acceptBtn = screen.getByRole('button', { name: /aceptar/i });
    expect(acceptBtn).toHaveAttribute('aria-disabled', 'false');
  });

  it('"Aceptar" is aria-disabled when transcribedText is empty', () => {
    render(<ControlButtons {...defaultProps} transcribedText="" />);

    const acceptBtn = screen.getByRole('button', { name: /aceptar/i });
    expect(acceptBtn).toHaveAttribute('aria-disabled', 'true');
  });

  it('"Aceptar" is aria-disabled when transcribedText is whitespace-only', () => {
    render(<ControlButtons {...defaultProps} transcribedText="   " />);

    const acceptBtn = screen.getByRole('button', { name: /aceptar/i });
    expect(acceptBtn).toHaveAttribute('aria-disabled', 'true');
  });

  it('"Aceptar" is aria-disabled when schema is not confirmed', () => {
    render(<ControlButtons {...defaultProps} hasConfirmedSchema={false} />);

    const acceptBtn = screen.getByRole('button', { name: /aceptar/i });
    expect(acceptBtn).toHaveAttribute('aria-disabled', 'true');
  });

  it('"Aceptar" is aria-disabled during LLM processing', () => {
    render(<ControlButtons {...defaultProps} isLLMProcessing={true} />);

    const acceptBtn = screen.getByRole('button', { name: /aceptar/i });
    expect(acceptBtn).toHaveAttribute('aria-disabled', 'true');
  });

  it('"Agregar nuevo" is enabled when not processing', () => {
    render(<ControlButtons {...defaultProps} />);

    const resetBtn = screen.getByRole('button', { name: /agregar nuevo/i });
    expect(resetBtn).toHaveAttribute('aria-disabled', 'false');
  });

  it('"Agregar nuevo" is aria-disabled during LLM processing', () => {
    render(<ControlButtons {...defaultProps} isLLMProcessing={true} />);

    const resetBtn = screen.getByRole('button', { name: /agregar nuevo/i });
    expect(resetBtn).toHaveAttribute('aria-disabled', 'true');
  });

  it('disables both buttons when the session is finalized', () => {
    render(<ControlButtons {...defaultProps} isFinalized={true} />);

    expect(screen.getByRole('button', { name: /aceptar/i })).toHaveAttribute(
      'aria-disabled',
      'true'
    );
    expect(screen.getByRole('button', { name: /agregar nuevo/i })).toHaveAttribute(
      'aria-disabled',
      'true'
    );
  });

  it('does not call onAccept when the session is finalized', () => {
    const onAccept = vi.fn();
    render(<ControlButtons {...defaultProps} isFinalized={true} onAccept={onAccept} />);

    fireEvent.click(screen.getByRole('button', { name: /aceptar/i }));
    expect(onAccept).not.toHaveBeenCalled();
  });

  it('calls onAccept when "Aceptar" is clicked with valid preconditions', () => {
    const onAccept = vi.fn();
    render(<ControlButtons {...defaultProps} onAccept={onAccept} />);

    fireEvent.click(screen.getByRole('button', { name: /aceptar/i }));
    expect(onAccept).toHaveBeenCalledTimes(1);
  });

  it('shows error message when "Aceptar" clicked without text', () => {
    render(<ControlButtons {...defaultProps} transcribedText="" />);

    fireEvent.click(screen.getByRole('button', { name: /aceptar/i }));
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Primero debe grabar y transcribir un audio.'
    );
  });

  it('shows error message when "Aceptar" clicked without confirmed schema', () => {
    render(<ControlButtons {...defaultProps} hasConfirmedSchema={false} />);

    fireEvent.click(screen.getByRole('button', { name: /aceptar/i }));
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Primero debe cargar y confirmar un archivo Excel.'
    );
  });

  it('does not call onAccept when preconditions are not met', () => {
    const onAccept = vi.fn();
    render(<ControlButtons {...defaultProps} transcribedText="" onAccept={onAccept} />);

    fireEvent.click(screen.getByRole('button', { name: /aceptar/i }));
    expect(onAccept).not.toHaveBeenCalled();
  });

  it('calls onReset when "Agregar nuevo" is clicked', () => {
    const onReset = vi.fn();
    render(<ControlButtons {...defaultProps} onReset={onReset} />);

    fireEvent.click(screen.getByRole('button', { name: /agregar nuevo/i }));
    expect(onReset).toHaveBeenCalledTimes(1);
  });

  it('does not call onReset during LLM processing', () => {
    const onReset = vi.fn();
    render(<ControlButtons {...defaultProps} isLLMProcessing={true} onReset={onReset} />);

    fireEvent.click(screen.getByRole('button', { name: /agregar nuevo/i }));
    expect(onReset).not.toHaveBeenCalled();
  });

  it('shows loading indicator on "Aceptar" during LLM processing', () => {
    const { container } = render(<ControlButtons {...defaultProps} isLLMProcessing={true} />);

    const spinner = container.querySelector('[class*="loadingIndicator"]');
    expect(spinner).toBeInTheDocument();
  });

  it('clears error message when "Agregar nuevo" is clicked', () => {
    render(<ControlButtons {...defaultProps} transcribedText="" />);

    // Trigger error
    fireEvent.click(screen.getByRole('button', { name: /aceptar/i }));
    expect(screen.getByRole('alert')).toBeInTheDocument();

    // Click "Agregar nuevo" to clear error
    fireEvent.click(screen.getByRole('button', { name: /agregar nuevo/i }));
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('error messages have role="alert" for accessibility', () => {
    render(<ControlButtons {...defaultProps} transcribedText="" />);

    fireEvent.click(screen.getByRole('button', { name: /aceptar/i }));
    const alert = screen.getByRole('alert');
    expect(alert).toBeInTheDocument();
  });

  it('buttons have descriptive aria-labels', () => {
    render(<ControlButtons {...defaultProps} />);

    expect(
      screen.getByLabelText('Aceptar texto transcrito y enviar para procesamiento')
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText('Agregar nuevo audio descartando el texto actual')
    ).toBeInTheDocument();
  });
});
