import { useState, useRef, useEffect } from 'react';
import { Info } from 'lucide-react';

interface Props {
  /** Short term being annotated, used as the accessible label. */
  term: string;
  /** Concise explanation. Keep under ~140 characters for readability. */
  text: string;
  /** Optional icon size. Defaults to 12. */
  size?: number;
  /** Optional className applied to the wrapper button. */
  className?: string;
}

/**
 * Minimal info icon with a hover/focus tooltip.
 *
 * Used sparingly for terms that benefit from a one-line definition:
 * - Decline %
 * - Sep / Dec share
 * - Ranking score
 * - First observed channel
 * - Canonical / unique cleaned-text post
 */
export function InfoTooltip({ term, text, size = 12, className }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLSpanElement | null>(null);

  // Close on outside click (for touch / keyboard users who toggle via Enter).
  useEffect(() => {
    if (!open) return;
    function onDocClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, [open]);

  return (
    <span
      ref={ref}
      className={`relative inline-flex items-center align-middle ${className ?? ''}`}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setOpen(v => !v);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        aria-label={`What is ${term}?`}
        className="inline-flex items-center justify-center text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-400 rounded-full"
      >
        <Info size={size} aria-hidden />
      </button>
      {open && (
        <span
          role="tooltip"
          className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 z-20 w-60 max-w-[16rem] rounded-md bg-slate-900 dark:bg-slate-700 text-slate-50 text-[11px] leading-snug px-2.5 py-1.5 shadow-lg whitespace-normal text-center"
        >
          {text}
        </span>
      )}
    </span>
  );
}
