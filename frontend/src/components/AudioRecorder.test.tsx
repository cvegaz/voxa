import { render, screen, fireEvent, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { AudioRecorder } from './AudioRecorder';

// Mock MediaRecorder
class MockMediaRecorder {
  state: string = 'inactive';
  ondataavailable: ((event: { data: Blob }) => void) | null = null;
  onstop: (() => void) | null = null;
  mimeType: string;

  static isTypeSupported = vi.fn((type: string) => type === 'audio/webm;codecs=opus');

  constructor(_stream: MediaStream, options?: MediaRecorderOptions) {
    this.mimeType = options?.mimeType || 'audio/webm';
  }

  start() {
    this.state = 'recording';
  }

  stop() {
    this.state = 'inactive';
    // Simulate data available
    if (this.ondataavailable) {
      this.ondataavailable({ data: new Blob(['audio-data'], { type: this.mimeType }) });
    }
    // Simulate stop event
    if (this.onstop) {
      this.onstop();
    }
  }
}

// Mock getUserMedia
const mockGetUserMedia = vi.fn();
const mockMediaStream = {
  getTracks: () => [{ stop: vi.fn() }],
} as unknown as MediaStream;

beforeEach(() => {
  vi.useFakeTimers();
  Object.defineProperty(globalThis, 'MediaRecorder', {
    writable: true,
    value: MockMediaRecorder,
  });
  Object.defineProperty(navigator, 'mediaDevices', {
    writable: true,
    value: { getUserMedia: mockGetUserMedia },
  });
  mockGetUserMedia.mockResolvedValue(mockMediaStream);
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe('AudioRecorder', () => {
  const defaultProps = {
    onRecordingComplete: vi.fn(),
    onError: vi.fn(),
  };

  it('renders "Grabar" button in idle state', () => {
    render(<AudioRecorder {...defaultProps} />);
    const button = screen.getByRole('button', { name: /iniciar grabación/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveTextContent('Grabar');
  });

  it('requests microphone permission on first press', async () => {
    render(<AudioRecorder {...defaultProps} />);
    const button = screen.getByRole('button', { name: /iniciar grabación/i });

    await act(async () => {
      fireEvent.click(button);
    });

    expect(mockGetUserMedia).toHaveBeenCalledWith({ audio: true });
  });

  it('shows "Detener" button while recording', async () => {
    render(<AudioRecorder {...defaultProps} />);
    const button = screen.getByRole('button', { name: /iniciar grabación/i });

    await act(async () => {
      fireEvent.click(button);
    });

    expect(screen.getByRole('button', { name: /detener grabación/i })).toHaveTextContent('Detener');
  });

  it('shows timer during recording', async () => {
    render(<AudioRecorder {...defaultProps} />);
    const button = screen.getByRole('button', { name: /iniciar grabación/i });

    await act(async () => {
      fireEvent.click(button);
    });

    expect(screen.getByRole('timer')).toHaveTextContent('00:00');
  });

  it('updates timer each second during recording', async () => {
    render(<AudioRecorder {...defaultProps} />);
    const button = screen.getByRole('button', { name: /iniciar grabación/i });

    await act(async () => {
      fireEvent.click(button);
    });

    // Advance time by 3 seconds
    await act(async () => {
      vi.advanceTimersByTime(3000);
    });

    expect(screen.getByRole('timer')).toHaveTextContent('00:03');
  });

  it('shows error when audio is too short (< 1 second)', async () => {
    render(<AudioRecorder {...defaultProps} />);
    const button = screen.getByRole('button', { name: /iniciar grabación/i });

    // Start recording
    await act(async () => {
      fireEvent.click(button);
    });

    // Stop immediately (0 seconds elapsed)
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /detener grabación/i }));
    });

    expect(screen.getByRole('alert')).toHaveTextContent(
      'El audio es demasiado corto (mínimo 1 segundo)'
    );
    expect(defaultProps.onError).toHaveBeenCalledWith(
      'El audio es demasiado corto (mínimo 1 segundo)'
    );
    expect(defaultProps.onRecordingComplete).not.toHaveBeenCalled();
  });

  it('calls onRecordingComplete with valid recording (>= 1 second)', async () => {
    render(<AudioRecorder {...defaultProps} />);
    const button = screen.getByRole('button', { name: /iniciar grabación/i });

    // Start recording
    await act(async () => {
      fireEvent.click(button);
    });

    // Advance 2 seconds
    await act(async () => {
      vi.advanceTimersByTime(2000);
    });

    // Stop recording
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /detener grabación/i }));
    });

    expect(defaultProps.onRecordingComplete).toHaveBeenCalledWith(
      expect.any(Blob),
      expect.any(Number),
      expect.any(String)
    );
  });

  it('shows permission denied error message', async () => {
    mockGetUserMedia.mockRejectedValueOnce(
      new DOMException('Permission denied', 'NotAllowedError')
    );

    render(<AudioRecorder {...defaultProps} />);
    const button = screen.getByRole('button', { name: /iniciar grabación/i });

    await act(async () => {
      fireEvent.click(button);
    });

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Se requiere acceso al micrófono para usar esta funcionalidad.'
    );
    expect(defaultProps.onError).toHaveBeenCalledWith(
      'Se requiere acceso al micrófono para usar esta funcionalidad.'
    );
  });

  it('shows hardware error message on device failure', async () => {
    mockGetUserMedia.mockRejectedValueOnce(
      new DOMException('Device not found', 'NotFoundError')
    );

    render(<AudioRecorder {...defaultProps} />);
    const button = screen.getByRole('button', { name: /iniciar grabación/i });

    await act(async () => {
      fireEvent.click(button);
    });

    expect(screen.getByRole('alert')).toHaveTextContent(
      'No se pudo acceder al dispositivo de audio.'
    );
  });

  it('disables button when isDisabled is true', () => {
    render(<AudioRecorder {...defaultProps} isDisabled={true} />);
    const button = screen.getByRole('button', { name: /iniciar grabación/i });
    expect(button).toBeDisabled();
  });

  it('shows spinner when status is processing', () => {
    render(<AudioRecorder {...defaultProps} status="processing" />);
    const button = screen.getByRole('button', { name: /procesando audio/i });
    expect(button).toBeDisabled();
  });

  it('auto-stops recording at 20 seconds', async () => {
    render(<AudioRecorder {...defaultProps} />);
    const button = screen.getByRole('button', { name: /iniciar grabación/i });

    // Start recording
    await act(async () => {
      fireEvent.click(button);
    });

    // Advance 20 seconds — the timer tick sets duration to 20, triggering auto-stop
    await act(async () => {
      vi.advanceTimersByTime(20000);
    });

    // The mock MediaRecorder.stop() synchronously fires onstop,
    // which calls onRecordingComplete since duration >= 1s
    expect(defaultProps.onRecordingComplete).toHaveBeenCalled();
  });

  it('can retry recording after an error', async () => {
    mockGetUserMedia.mockRejectedValueOnce(
      new DOMException('Permission denied', 'NotAllowedError')
    );

    render(<AudioRecorder {...defaultProps} />);
    const button = screen.getByRole('button', { name: /iniciar grabación/i });

    // First attempt fails
    await act(async () => {
      fireEvent.click(button);
    });

    expect(screen.getByRole('alert')).toBeInTheDocument();

    // Reset mock for success
    mockGetUserMedia.mockResolvedValueOnce(mockMediaStream);

    // Second attempt should work
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /iniciar grabación/i }));
    });

    expect(screen.getByRole('button', { name: /detener grabación/i })).toHaveTextContent('Detener');
  });

  it('shows a Bluetooth warning when the active mic is a Bluetooth device', async () => {
    const bluetoothStream = {
      getTracks: () => [{ stop: vi.fn(), label: 'AirPods Pro' }],
      getAudioTracks: () => [{ stop: vi.fn(), label: 'AirPods Pro' }],
    } as unknown as MediaStream;
    mockGetUserMedia.mockResolvedValueOnce(bluetoothStream);

    render(<AudioRecorder {...defaultProps} />);

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /iniciar grabación/i }));
    });

    expect(screen.getByText(/micrófono Bluetooth/i)).toBeInTheDocument();
  });

  it('does not show a Bluetooth warning for a wired/built-in mic', async () => {
    const wiredStream = {
      getTracks: () => [{ stop: vi.fn(), label: 'MacBook Pro Microphone' }],
      getAudioTracks: () => [{ stop: vi.fn(), label: 'MacBook Pro Microphone' }],
    } as unknown as MediaStream;
    mockGetUserMedia.mockResolvedValueOnce(wiredStream);

    render(<AudioRecorder {...defaultProps} />);

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /iniciar grabación/i }));
    });

    expect(screen.queryByText(/micrófono Bluetooth/i)).not.toBeInTheDocument();
  });

  it('has proper aria attributes for accessibility', async () => {
    render(<AudioRecorder {...defaultProps} />);

    // Idle state
    const button = screen.getByRole('button', { name: /iniciar grabación/i });
    expect(button).toHaveAttribute('aria-label', 'Iniciar grabación de audio');

    // Recording state
    await act(async () => {
      fireEvent.click(button);
    });

    const timer = screen.getByRole('timer');
    expect(timer).toHaveAttribute('aria-live', 'polite');
  });
});
