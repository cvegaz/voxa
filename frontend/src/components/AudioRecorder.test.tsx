import { render, screen, fireEvent, act } from '@testing-library/react';
import {
  describe,
  it,
  expect,
  vi,
  beforeEach,
  afterEach,
  onTestFinished,
} from 'vitest';
import { AudioRecorder } from './AudioRecorder';

// Mock MediaRecorder
class MockMediaRecorder {
  state: string = 'inactive';
  ondataavailable: ((event: { data: Blob }) => void) | null = null;
  onstop: (() => void) | null = null;
  mimeType: string;

  // Typed explicitly as `=> boolean`: without the annotation TypeScript infers a
  // type predicate (`type is 'audio/webm;codecs=opus'`) from the comparison, and
  // then no other stub can be assigned to it.
  static isTypeSupported = vi.fn<(type: string) => boolean>(
    (type) => type === 'audio/webm;codecs=opus'
  );

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

  it('calls onRecordingStart when a recording begins', async () => {
    const onRecordingStart = vi.fn();
    render(<AudioRecorder {...defaultProps} onRecordingStart={onRecordingStart} />);
    const button = screen.getByRole('button', { name: /iniciar grabación/i });

    await act(async () => {
      fireEvent.click(button);
    });

    expect(onRecordingStart).toHaveBeenCalledTimes(1);
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

/**
 * ADR-0019 §1 — the cap must be a budget the user can pace against.
 *
 * Before this, nothing in the UI mentioned a duration: the auto-stop simply cut
 * the narration mid-word. That is the failure mode the whole "keep 20s" decision
 * was made to avoid, so it is worth pinning down in tests.
 */
describe('AudioRecorder — communicating the recording budget', () => {
  const defaultProps = {
    onRecordingComplete: vi.fn(),
    onError: vi.fn(),
  };

  it('states the limit before recording starts', () => {
    render(<AudioRecorder {...defaultProps} />);
    expect(screen.getByText(/máximo 20 segundos por grabación/i)).toBeInTheDocument();
  });

  it('reflects a custom cap in the stated limit', () => {
    render(<AudioRecorder {...defaultProps} maxDurationSeconds={45} />);
    expect(screen.getByText(/máximo 45 segundos por grabación/i)).toBeInTheDocument();
  });

  it('shows elapsed time against the limit while recording', async () => {
    render(<AudioRecorder {...defaultProps} />);

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /iniciar grabación/i }));
    });
    await act(async () => {
      vi.advanceTimersByTime(3000);
    });

    expect(screen.getByRole('timer')).toHaveTextContent('00:03 / 00:20');
  });

  it('hides the static hint while recording (the timer carries it)', async () => {
    render(<AudioRecorder {...defaultProps} />);

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /iniciar grabación/i }));
    });

    expect(screen.queryByText(/máximo 20 segundos/i)).not.toBeInTheDocument();
  });

  it('warns in the final stretch so the user can wrap up', async () => {
    render(<AudioRecorder {...defaultProps} />);

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /iniciar grabación/i }));
    });

    // 14s elapsed -> 6s left: still outside the warning window.
    await act(async () => {
      vi.advanceTimersByTime(14000);
    });
    expect(screen.queryByText(/te quedan/i)).not.toBeInTheDocument();

    // 16s elapsed -> 4s left: warn.
    await act(async () => {
      vi.advanceTimersByTime(2000);
    });
    expect(screen.getByText(/te quedan 4 s/i)).toBeInTheDocument();
  });
});

/**
 * ADR-0019 §6 — capability detection, never user-agent sniffing.
 *
 * A silent failure here is worse than it looks: the visitor concludes the product
 * does not work and leaves, and the month's headline metric (sessions reaching a
 * first narration) records it as disinterest rather than as a broken environment.
 */
describe('AudioRecorder — capability detection', () => {
  const defaultProps = {
    onRecordingComplete: vi.fn(),
    onError: vi.fn(),
  };

  it('explains the problem when MediaRecorder is missing', () => {
    Object.defineProperty(globalThis, 'MediaRecorder', {
      writable: true,
      value: undefined,
    });

    render(<AudioRecorder {...defaultProps} />);

    expect(screen.getByRole('alert')).toHaveTextContent(/no puede grabar audio/i);
    expect(screen.getByRole('button', { name: /iniciar grabación/i })).toBeDisabled();
  });

  it('explains the problem outside a secure context (no mediaDevices)', () => {
    // navigator.mediaDevices is undefined on plain HTTP — the microphone is
    // unreachable and this is exactly how a broken HTTPS deploy would present.
    Object.defineProperty(navigator, 'mediaDevices', {
      writable: true,
      value: undefined,
    });

    render(<AudioRecorder {...defaultProps} />);

    expect(screen.getByRole('alert')).toHaveTextContent(/https/i);
    expect(screen.getByRole('button', { name: /iniciar grabación/i })).toBeDisabled();
  });

  it('still allows recording when no candidate MIME type is supported', () => {
    // Safari reports false for our candidates yet records fine with the browser's
    // own container. Rejecting here would be a false negative that turns a
    // working browser away — the costliest possible mistake for a demo.
    // Restored explicitly: reassigning a static is not undone by restoreAllMocks.
    const original = MockMediaRecorder.isTypeSupported;
    MockMediaRecorder.isTypeSupported = vi.fn<(type: string) => boolean>(() => false);
    onTestFinished(() => {
      MockMediaRecorder.isTypeSupported = original;
    });

    render(<AudioRecorder {...defaultProps} />);

    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /iniciar grabación/i })
    ).not.toBeDisabled();
  });
});
