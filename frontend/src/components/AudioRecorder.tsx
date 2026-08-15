import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { IconMic, IconStop, IconHeadphones, IconAlert } from './Icons';
import { useI18n } from '../i18n/LanguageContext';
import styles from './AudioRecorder.module.css';

export interface AudioRecorderProps {
  /** Called when a valid recording is completed */
  onRecordingComplete: (audioBlob: Blob, duration: number, mimeType: string) => void;
  /** Called when an error occurs */
  onError: (error: string) => void;
  /** Called when a new recording starts (e.g. to clear previously shown text) */
  onRecordingStart?: () => void;
  /** Disable the recorder (e.g. during LLM processing) */
  isDisabled?: boolean;
  /** External status override */
  status?: 'idle' | 'recording' | 'processing' | 'error';
  /**
   * Maximum recording length in seconds before auto-stop. Defaults to the
   * free-tier cap; a future paid tier can pass a larger value.
   */
  maxDurationSeconds?: number;
}

type RecorderStatus = 'idle' | 'recording' | 'processing' | 'error';

/**
 * Cap for a single recording, in seconds.
 *
 * This auto-stop is **UX, not enforcement** (ADR-0019 §1). The real control is
 * server-side: the backend MEASURES the uploaded file with ffprobe and rejects
 * anything longer, because a client-reported duration can be forged and an upload
 * never goes through this component at all. What this constant does is let the
 * user pace the narration against a budget they can see.
 *
 * Kept numerically in sync with `MAX_AUDIO_DURATION_SECONDS` in
 * `backend/app/constants.py`.
 */
const DEFAULT_MAX_DURATION_SECONDS = 20;
const MIN_DURATION_SECONDS = 1;

/** Seconds of "wrap it up" warning before the auto-stop fires. */
const WARN_REMAINING_SECONDS = 5;

const CANDIDATE_MIME_TYPES = ['audio/webm;codecs=opus', 'audio/ogg', 'audio/webm'];

/**
 * Determines the best supported MIME type for MediaRecorder.
 * Tries audio/webm;codecs=opus first, then audio/ogg, then audio/webm.
 */
function getSupportedMimeType(): string {
  for (const type of CANDIDATE_MIME_TYPES) {
    if (MediaRecorder.isTypeSupported?.(type)) {
      return type;
    }
  }
  // Fallback — let the browser pick
  return '';
}

/**
 * Can this browser record at all? (ADR-0019 §6)
 *
 * This is **capability detection**, not user-agent sniffing. We ask the platform
 * what it can do instead of guessing from its name: UA strings are self-reported
 * and any browser-to-feature table rots within a year.
 *
 * It catches the two failures that are genuinely fatal and otherwise silent:
 *   - `navigator.mediaDevices` is undefined outside a **secure context**, so a page
 *     served over plain HTTP (anything but localhost) cannot reach the microphone;
 *   - `MediaRecorder` is missing entirely on older browsers.
 *
 * Deliberately NOT treated as unsupported: "none of our candidate MIME types is
 * supported". `getSupportedMimeType()` falls back to `''`, which lets the browser
 * choose its own container — Safari records fine that way. Rejecting there would
 * be a false negative that turns a working browser away, and losing a visitor
 * costs far more than an occasional failed attempt.
 */
function isRecordingSupported(): boolean {
  if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
    return false;
  }
  return typeof MediaRecorder !== 'undefined';
}

/**
 * Formats seconds into MM:SS display string.
 */
function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

/**
 * Heuristic to flag a wireless/Bluetooth input from its device label. A Bluetooth
 * mic is forced onto the low-fidelity HFP/HSP profile (mono, ~8-16 kHz), which
 * degrades transcription. We can't change the profile from the web, so we warn
 * the user so they can switch to the built-in or a wired/USB mic instead.
 */
function isLikelyBluetoothLabel(label: string): boolean {
  return /airpods|bluetooth|inalámbric|wireless|headset|hands-?free|manos\s*libres|buds|beats/i.test(
    label
  );
}

/**
 * Reads the label of the active audio track from a captured stream, tolerating
 * the slightly different shapes browsers expose (getAudioTracks vs getTracks).
 */
function getActiveInputLabel(stream: MediaStream): string {
  const track = stream.getAudioTracks?.()[0] ?? stream.getTracks?.()[0] ?? null;
  return track?.label ?? '';
}

/**
 * AudioRecorder component that handles microphone capture using MediaRecorder API.
 *
 * Features:
 * - Requests microphone permission on first press
 * - Toggle recording on button press (start/stop)
 * - Red pulse animation and timer during recording
 * - Auto-stop at the max duration (default 20s, configurable)
 * - Client-side duration validation (reject < 1s)
 * - Permission denied and hardware error handling
 */
export function AudioRecorder({
  onRecordingComplete,
  onError,
  onRecordingStart,
  isDisabled = false,
  status: externalStatus,
  maxDurationSeconds = DEFAULT_MAX_DURATION_SECONDS,
}: AudioRecorderProps) {
  const { t } = useI18n();
  const [internalStatus, setInternalStatus] = useState<RecorderStatus>('idle');
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState<string | null>(null);
  // True when the captured input looks like a Bluetooth mic (low-quality HFP).
  const [isBluetoothInput, setIsBluetoothInput] = useState(false);

  // Evaluated once on mount rather than at module load: the capability depends on
  // the runtime environment, and reading it at import time would freeze whatever
  // the module system happened to see first.
  const canRecord = useMemo(() => isRecordingSupported(), []);

  // Countdown, so the cap is a budget the user can pace against instead of a
  // surprise cut mid-word.
  const remainingSeconds = Math.max(0, maxDurationSeconds - duration);
  const isEndingSoon = remainingSeconds <= WARN_REMAINING_SECONDS;

  // The recording lifecycle is owned internally: while we're actively
  // recording, that state must win so the button shows "Detener" and can stop.
  // For every other phase we let the parent override (e.g. force 'processing'
  // during transcription, or reset back to 'idle' afterwards).
  const status =
    internalStatus === 'recording' ? 'recording' : externalStatus ?? internalStatus;

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number>(0);
  const streamRef = useRef<MediaStream | null>(null);
  const mimeTypeRef = useRef<string>('');

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopTimer();
      stopMediaStream();
    };
  }, []);

  const stopTimer = useCallback(() => {
    if (timerRef.current !== null) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const stopMediaStream = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  }, []);

  const startTimer = useCallback(() => {
    startTimeRef.current = Date.now();
    timerRef.current = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startTimeRef.current) / 1000);
      setDuration(elapsed);
    }, 1000);
  }, []);

  const handleStop = useCallback(
    (recorder: MediaRecorder) => {
      recorder.onstop = () => {
        stopTimer();
        const elapsedSeconds = Math.floor(
          (Date.now() - startTimeRef.current) / 1000
        );

        if (elapsedSeconds < MIN_DURATION_SECONDS) {
          const errorMsg = t('recorder.tooShort');
          setError(errorMsg);
          setInternalStatus('error');
          onError(errorMsg);
          chunksRef.current = [];
          stopMediaStream();
          return;
        }

        const mimeType = mimeTypeRef.current || 'audio/webm';
        const blob = new Blob(chunksRef.current, { type: mimeType });
        chunksRef.current = [];
        stopMediaStream();

        setInternalStatus('processing');
        onRecordingComplete(blob, elapsedSeconds, mimeType);
      };
    },
    [onRecordingComplete, onError, stopTimer, stopMediaStream, t]
  );

  const startRecording = useCallback(async () => {
    setError(null);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // Detect whether the active mic is Bluetooth so we can warn the user that
      // its low-fidelity HFP profile hurts transcription accuracy.
      setIsBluetoothInput(isLikelyBluetoothLabel(getActiveInputLabel(stream)));

      const mimeType = getSupportedMimeType();
      mimeTypeRef.current = mimeType;

      const options: MediaRecorderOptions = mimeType ? { mimeType } : {};
      const recorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      handleStop(recorder);

      recorder.start();
      setInternalStatus('recording');
      setDuration(0);
      startTimer();
      // Signal the start so the parent can clear any previously shown text.
      onRecordingStart?.();
    } catch (err: unknown) {
      let errorMsg: string;

      if (err instanceof DOMException) {
        if (
          err.name === 'NotAllowedError' ||
          err.name === 'PermissionDeniedError'
        ) {
          errorMsg = t('recorder.permissionDenied');
        } else {
          errorMsg = t('recorder.deviceError');
        }
      } else {
        errorMsg = t('recorder.deviceError');
      }

      setError(errorMsg);
      setInternalStatus('error');
      onError(errorMsg);
    }
  }, [handleStop, startTimer, onError, onRecordingStart, t]);

  const stopRecording = useCallback(() => {
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state === 'recording'
    ) {
      mediaRecorderRef.current.stop();
    }
  }, []);

  // Auto-stop once the recording reaches the max duration.
  useEffect(() => {
    if (status === 'recording' && duration >= maxDurationSeconds) {
      stopRecording();
    }
  }, [status, duration, maxDurationSeconds, stopRecording]);

  const handleButtonClick = useCallback(() => {
    if (status === 'recording') {
      stopRecording();
    } else if (status === 'idle' || status === 'error') {
      startRecording();
    }
  }, [status, stopRecording, startRecording]);

  const getButtonLabel = (): string => {
    switch (status) {
      case 'recording':
        return t('recorder.stop');
      case 'processing':
        return '';
      default:
        return t('recorder.record');
    }
  };

  const getAriaLabel = (): string => {
    switch (status) {
      case 'recording':
        return t('recorder.ariaStop');
      case 'processing':
        return t('recorder.ariaProcessing');
      default:
        return t('recorder.ariaStart');
    }
  };

  const isButtonDisabled = isDisabled || status === 'processing' || !canRecord;

  const buttonClasses = [
    styles.recordButton,
    status === 'recording' ? styles.recordButtonRecording : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={styles.container}>
      <button
        type="button"
        className={buttonClasses}
        onClick={handleButtonClick}
        disabled={isButtonDisabled}
        aria-label={getAriaLabel()}
      >
        {status === 'processing' ? (
          <span className={styles.spinner} aria-hidden="true" />
        ) : (
          <>
            {status === 'recording' ? (
              <IconStop aria-hidden="true" />
            ) : (
              <IconMic aria-hidden="true" />
            )}
            {getButtonLabel()}
          </>
        )}
      </button>

      {/* State the budget BEFORE recording. Until now nothing in the UI mentioned
          a duration at all, so the auto-stop arrived as a surprise. */}
      {canRecord && status !== 'recording' && (
        <p className={styles.limitHint}>
          {t('recorder.limitHint', { seconds: String(maxDurationSeconds) })}
        </p>
      )}

      {status === 'recording' && (
        <div className={styles.timerContainer}>
          <span className={styles.pulseIndicator} aria-hidden="true" />
          <span
            className={[styles.timer, isEndingSoon ? styles.timerWarning : '']
              .filter(Boolean)
              .join(' ')}
            role="timer"
            aria-live="polite"
            aria-label={t('recorder.ariaTimer', {
              time: formatTime(duration),
              limit: formatTime(maxDurationSeconds),
            })}
          >
            {formatTime(duration)} / {formatTime(maxDurationSeconds)}
          </span>
        </div>
      )}

      {/* Final stretch: an explicit "wrap up" cue, announced to screen readers
          too, so the cut is never the first notice the user gets. */}
      {status === 'recording' && isEndingSoon && (
        <p className={styles.timeLeft} role="status" aria-live="polite">
          {t('recorder.timeLeft', { seconds: String(remainingSeconds) })}
        </p>
      )}

      {!canRecord && (
        <div className={styles.warningContainer} role="alert" aria-live="assertive">
          <span className={styles.warningIcon} aria-hidden="true">
            <IconAlert />
          </span>
          <p className={styles.warningMessage}>{t('recorder.unsupported')}</p>
        </div>
      )}

      {isBluetoothInput && (
        <div className={styles.warningContainer} role="status" aria-live="polite">
          <span className={styles.warningIcon} aria-hidden="true">
            <IconHeadphones />
          </span>
          <p className={styles.warningMessage}>{t('recorder.bluetoothWarning')}</p>
        </div>
      )}

      {status === 'error' && error && (
        <div className={styles.errorContainer} role="alert" aria-live="assertive">
          <span className={styles.errorIcon} aria-hidden="true">
            <IconAlert />
          </span>
          <p className={styles.errorMessage}>{error}</p>
        </div>
      )}
    </div>
  );
}
