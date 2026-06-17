import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { TranscriptionDisplay } from './TranscriptionDisplay';

describe('TranscriptionDisplay', () => {
  const defaultProps = {
    text: '',
    isLoading: false,
    isDisabled: false,
    onChange: vi.fn(),
  };

  it('renders an editable textarea with the correct label', () => {
    render(<TranscriptionDisplay {...defaultProps} />);
    const textarea = screen.getByLabelText('Texto transcrito');
    expect(textarea).toBeInTheDocument();
    expect(textarea).toBeEnabled();
  });

  it('displays the provided text value', () => {
    render(<TranscriptionDisplay {...defaultProps} text="Hola mundo" />);
    const textarea = screen.getByLabelText('Texto transcrito');
    expect(textarea).toHaveValue('Hola mundo');
  });

  it('shows placeholder when text is empty', () => {
    render(<TranscriptionDisplay {...defaultProps} />);
    const textarea = screen.getByPlaceholderText('El texto transcrito aparecerá aquí...');
    expect(textarea).toBeInTheDocument();
  });

  it('calls onChange on every keystroke', () => {
    const onChange = vi.fn();
    render(<TranscriptionDisplay {...defaultProps} onChange={onChange} />);
    const textarea = screen.getByLabelText('Texto transcrito');
    fireEvent.change(textarea, { target: { value: 'Nuevo texto' } });
    expect(onChange).toHaveBeenCalledWith('Nuevo texto');
  });

  it('shows spinner overlay and disables textarea when isLoading is true', () => {
    render(<TranscriptionDisplay {...defaultProps} isLoading={true} />);
    const textarea = screen.getByLabelText('Texto transcrito');
    expect(textarea).toBeDisabled();
    expect(screen.getByRole('status', { name: 'Transcribiendo audio' })).toBeInTheDocument();
  });

  it('sets aria-busy on the container when loading', () => {
    const { container } = render(<TranscriptionDisplay {...defaultProps} isLoading={true} />);
    const wrapper = container.firstElementChild;
    expect(wrapper).toHaveAttribute('aria-busy', 'true');
  });

  it('does not show spinner when not loading', () => {
    render(<TranscriptionDisplay {...defaultProps} isLoading={false} />);
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('disables textarea when isDisabled is true', () => {
    render(<TranscriptionDisplay {...defaultProps} isDisabled={true} />);
    const textarea = screen.getByLabelText('Texto transcrito');
    expect(textarea).toBeDisabled();
  });

  it('textarea is enabled when neither loading nor disabled', () => {
    render(<TranscriptionDisplay {...defaultProps} isLoading={false} isDisabled={false} />);
    const textarea = screen.getByLabelText('Texto transcrito');
    expect(textarea).toBeEnabled();
  });

  it('renders with minimum 4 rows', () => {
    render(<TranscriptionDisplay {...defaultProps} />);
    const textarea = screen.getByLabelText('Texto transcrito');
    expect(textarea).toHaveAttribute('rows', '4');
  });

  it('clears text when parent passes empty string (error/reset scenario)', () => {
    const { rerender } = render(
      <TranscriptionDisplay {...defaultProps} text="Texto transcrito previo" />
    );
    const textarea = screen.getByLabelText('Texto transcrito');
    expect(textarea).toHaveValue('Texto transcrito previo');

    rerender(<TranscriptionDisplay {...defaultProps} text="" />);
    expect(textarea).toHaveValue('');
  });
});
