import { useI18n } from '../i18n/LanguageContext';
import { IconMic, IconCheck, IconArrowRight } from './Icons';
import { RECORD_COUNT, rowsFilled } from './mockupTimeline';
import { useMockupLoop } from './useMockupLoop';
import styles from './AudioToExcelMockup.module.css';

// Bar heights (%) for the faux waveform. Static markup; CSS animates them.
const BARS = [40, 70, 30, 90, 55, 75, 35, 85, 50, 65, 45, 80];

/** i18n key prefixes for the two narrated examples. */
const RECORDS = ['mockup.ex1', 'mockup.ex2'] as const;

/**
 * Animated illustration of the Voxa flow for the hero: a microphone waveform →
 * a sentence transcribed fragment by fragment → Accept → a row landing in the
 * sheet. Twice, into the SAME sheet, so the message is not just "it transcribes"
 * but "rows accumulate" — which is the actual product: one template, many
 * narrations.
 *
 * A third row holds a permanent "…" so the loop can stop at two records without
 * implying that two is the limit. Twenty seconds of hero animation is longer
 * than anyone watches; the ellipsis buys the same meaning for free.
 *
 * The choreography lives in mockupTimeline.ts and the loop control in
 * useMockupLoop.ts — this file only renders a step.
 */
export function AudioToExcelMockup() {
  const { t } = useI18n();
  const { containerRef, step, reduced } = useMockupLoop();

  const prefix = RECORDS[step.record];
  const fragments = [
    t(`${prefix}.say1` as never),
    t(`${prefix}.say2` as never),
    t(`${prefix}.say3` as never),
  ];
  const spoken = fragments.slice(0, step.revealed).join(', ');
  const filled = rowsFilled(step);

  const isRecording = step.phase === 'recording';
  const isConfirming = step.phase === 'confirming';
  // The sentence stays up through `committed` and `resting`: clearing it the
  // moment the row lands leaves an empty card in the middle of the hero, and
  // keeping it lets the viewer read what produced the row they just saw
  // appear. It clears on its own when the next recording begins.
  const showTranscript = step.revealed > 0;

  return (
    <div
      ref={containerRef}
      className={styles.mockup}
      role="img"
      aria-label={t('mockup.ariaLabel')}
    >
      {/* 1. Voice capture */}
      <div className={`${styles.card} ${styles.voice}`}>
        <span className={styles.badge}>
          <span
            className={`${styles.recDot} ${isRecording ? styles.recDotLive : ''}`}
            aria-hidden="true"
          />
          {t('mockup.recording')}
        </span>
        <span className={styles.micIcon} aria-hidden="true">
          <IconMic size={18} />
        </span>
        <div
          className={`${styles.wave} ${isRecording ? styles.waveLive : ''}`}
          aria-hidden="true"
        >
          {BARS.map((h, i) => (
            <span
              key={i}
              className={styles.bar}
              style={{ height: `${h}%`, animationDelay: `${i * 0.08}s` }}
            />
          ))}
        </div>
      </div>

      <div className={styles.connector} aria-hidden="true" />

      {/* 2. Transcript, revealed fragment by fragment, then the Accept chip */}
      <div className={`${styles.card} ${styles.transcript}`}>
        <span className={styles.badge}>{t('mockup.transcribing')}</span>
        {/* The line keeps its height whether or not there is text: an empty
            paragraph collapsing would make the whole hero jump every loop. */}
        <p className={styles.spoken}>
          {showTranscript ? `«${spoken}` : ' '}
          {showTranscript && step.revealed < 3 && (
            <span className={styles.caret} aria-hidden="true" />
          )}
          {showTranscript && step.revealed === 3 && '»'}
        </p>
        <span
          className={`${styles.accept} ${isConfirming ? styles.acceptOn : ''}`}
          aria-hidden="true"
        >
          {t('mockup.accept')}
          <IconArrowRight size={13} />
        </span>
      </div>

      <div className={styles.connector} aria-hidden="true" />

      {/* 3. The sheet. All rows are always rendered so the card never changes
             height — a hero that resizes on every loop is layout shift the
             visitor feels even if they cannot name it. */}
      <div className={`${styles.card} ${styles.sheet}`}>
        {/* The label follows reality: "Fila añadida" only once one has been.
            Announcing it over an empty table is a small lie the visitor can
            see, and this card is on screen from the very first frame. */}
        <span
          className={`${styles.badge} ${filled > 0 ? styles.badgeDone : ''}`}
        >
          {filled > 0 && <IconCheck size={14} />}
          {filled > 0 ? t('mockup.done') : t('mockup.sheet')}
        </span>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>{t('mockup.colVenue')}</th>
              <th>{t('mockup.colCapacity')}</th>
              <th>{t('mockup.colDate')}</th>
            </tr>
          </thead>
          <tbody>
            {RECORDS.map((key, i) => {
              const isIn = i < filled;
              // The key flips with `isIn`, which remounts the row as it lands.
              // Without that React would reuse the node and the fill animation
              // would play once ever, instead of on every loop.
              return (
                <tr
                  key={`${key}-${isIn ? 'in' : 'out'}`}
                  className={`${styles.row} ${isIn ? styles.rowIn : styles.rowEmpty}`}
                >
                  <td>{isIn ? t(`${key}.venue` as never) : ' '}</td>
                  <td>{isIn ? t(`${key}.capacity` as never) : ''}</td>
                  <td>{isIn ? t(`${key}.date` as never) : ''}</td>
                </tr>
              );
            })}
            <tr className={styles.rowMore}>
              <td colSpan={3} title={t('mockup.more')}>
                {filled === RECORD_COUNT || reduced ? '…' : ' '}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
