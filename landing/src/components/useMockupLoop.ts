import { useEffect, useRef, useState } from 'react';
import { TIMELINE, type Step } from './mockupTimeline';

/** Final frame: everything narrated, every row in. */
const FINAL_STEP: Step = TIMELINE[TIMELINE.length - 1];

function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * Drives the hero mockup's loop, and knows when NOT to.
 *
 * Three things decide whether the animation runs, and all three matter:
 *
 * - **Reduced motion.** A user who asked the OS to stop animations gets the
 *   finished frame and no timer at all. The point of the mockup is the end
 *   state, so freezing it loses nothing; the CSS already honoured this and
 *   moving to JS must not quietly drop it.
 * - **Off-screen.** This is a hero on a scrolling page. An infinite loop that
 *   keeps ticking while the visitor reads the footer burns CPU for nobody.
 * - **Hidden tab.** Marketing pages get left open for hours. Browsers already
 *   throttle background timers, but stopping outright is honest and makes the
 *   loop resume from a clean step instead of a throttled, drifted one.
 *
 * Returns the current step plus the ref to attach to the animated element.
 */
export function useMockupLoop() {
  const containerRef = useRef<HTMLDivElement>(null);
  const reduced = prefersReducedMotion();
  const [index, setIndex] = useState(0);
  const [running, setRunning] = useState(!reduced);

  // Pause when scrolled out of view or when the tab is hidden.
  useEffect(() => {
    if (reduced) return;

    const element = containerRef.current;
    let visible = true;
    let onScreen = true;

    const sync = () => setRunning(visible && onScreen);

    const onVisibility = () => {
      visible = document.visibilityState === 'visible';
      sync();
    };
    document.addEventListener('visibilitychange', onVisibility);

    // IntersectionObserver is absent in jsdom and in older browsers; without it
    // the loop simply always runs, which is the previous behaviour rather than
    // a broken one.
    let observer: IntersectionObserver | undefined;
    if (element && typeof IntersectionObserver !== 'undefined') {
      observer = new IntersectionObserver(
        (entries) => {
          onScreen = entries.some((e) => e.isIntersecting);
          sync();
        },
        { threshold: 0.15 }
      );
      observer.observe(element);
    }

    return () => {
      document.removeEventListener('visibilitychange', onVisibility);
      observer?.disconnect();
    };
  }, [reduced]);

  // One timer, re-armed per step, rather than one interval for the whole
  // loop: steps have different durations, and a single interval would force
  // every phase to share the shortest one.
  useEffect(() => {
    if (!running) return;
    const timer = setTimeout(
      () => setIndex((i) => (i + 1) % TIMELINE.length),
      TIMELINE[index].ms
    );
    return () => clearTimeout(timer);
  }, [index, running]);

  return {
    containerRef,
    step: reduced ? FINAL_STEP : TIMELINE[index],
    reduced,
  };
}
