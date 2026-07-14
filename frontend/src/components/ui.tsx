// Small shared presentational components and an icon map.
import type { ReactNode } from "react";
import type { Source } from "../lib/types";

/** Citation block shown with answer feedback so learners can verify against docs. */
export function SourceCite({ source }: { source: Source }) {
  return (
    <div className="mt-3 rounded-lg border border-charcoal-border bg-charcoal-light/50 p-3 text-sm">
      {source.quote && (
        <p className="mb-2 italic text-slate-300">&ldquo;{source.quote}&rdquo;</p>
      )}
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
        <span className="font-semibold uppercase tracking-wider text-slate-500">
          Source
        </span>
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          className="font-semibold text-iris-light underline-offset-2 hover:underline"
        >
          {source.label} ↗
        </a>
        {source.url2 && (
          <>
            <span className="text-slate-500">·</span>
            <a
              href={source.url2}
              target="_blank"
              rel="noopener noreferrer"
              className="font-semibold text-iris-light underline-offset-2 hover:underline"
            >
              {source.label2 || "Additional reference"} ↗
            </a>
          </>
        )}
        {source.page && <span className="text-slate-500">· {source.page}</span>}
      </div>
    </div>
  );
}

const ICONS: Record<string, string> = {
  rocket: "🚀",
  refresh: "🔄",
  gauge: "📊",
  badge: "🎖️",
  book: "📘",
  trophy: "🏆",
  star: "⭐",
  crown: "👑",
  cap: "🎓",
};

export function Icon({ name, className = "" }: { name: string; className?: string }) {
  return (
    <span className={className} role="img" aria-label={name}>
      {ICONS[name] ?? "✨"}
    </span>
  );
}

export function Spinner() {
  return (
    <div className="flex items-center justify-center py-20">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-charcoal-border border-t-iris" />
    </div>
  );
}

export function XpBar({
  level,
  total,
  toNext,
}: {
  level: number;
  total: number;
  toNext: number;
}) {
  // Width within the current level band (band size = level * 100).
  const band = level * 100;
  const into = band - toNext;
  const pct = Math.max(4, Math.min(100, (into / band) * 100));
  return (
    <div className="w-full">
      <div className="mb-1 flex items-center justify-between text-xs text-slate-400">
        <span className="font-semibold text-iris-light">Level {level}</span>
        <span>{toNext} XP to next level</span>
      </div>
      <div className="h-2.5 w-full overflow-hidden rounded-full bg-charcoal-light">
        <div
          className="h-full rounded-full bg-gradient-to-r from-iris to-iris-light transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="mt-1 text-right text-xs text-slate-500">{total} XP total</div>
    </div>
  );
}

export function Pill({ children }: { children: ReactNode }) {
  return <span className="chip">{children}</span>;
}

export function DifficultyTag({ difficulty }: { difficulty: string }) {
  const styles: Record<string, string> = {
    core: "text-emerald-300 border-emerald-500/30 bg-emerald-500/10",
    intermediate: "text-amber-300 border-amber-500/30 bg-amber-500/10",
    advanced: "text-rose-300 border-rose-500/30 bg-rose-500/10",
  };
  return (
    <span
      className={`rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize ${
        styles[difficulty] ?? styles.core
      }`}
    >
      {difficulty}
    </span>
  );
}
