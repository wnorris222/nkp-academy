import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Icon, Spinner } from "../components/ui";
import { api } from "../lib/api";
import type { CardKind, Deck, Flashcard, FlashcardDeck } from "../lib/types";

type Mark = "known" | "unknown";

/** The "all" deck is the everything-at-once option; it gets the hero slot. */
const DECK_ALL = "all";

const KIND_STYLES: Record<CardKind, string> = {
  term: "border-sky-500/40 text-sky-300",
  concept: "border-iris/40 text-iris-light",
  command: "border-amber-500/40 text-amber-300",
  fact: "border-emerald-500/40 text-emerald-300",
};

/** Render `backticked` spans in authored prose as inline code.
 *
 * Card text names literal things — a namespace called `kommander`, a flag
 * called `--self-managed` — and the decks mark those the way the Nutanix docs
 * do. Splitting on the backtick leaves code spans at the odd indices; an
 * unmatched backtick just falls through as text rather than breaking the card.
 */
function RichText({ text }: { text: string }) {
  return (
    <>
      {text.split("`").map((part, i) =>
        i % 2 === 1 ? (
          <code key={i} className="rounded bg-charcoal px-1 py-0.5 text-[0.9em] text-iris-light">
            {part}
          </code>
        ) : (
          part
        ),
      )}
    </>
  );
}

/** Fisher-Yates — returns a new array, leaves the source order untouched. */
function shuffled<T>(items: T[]): T[] {
  const out = [...items];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

/* ---------------- Deck picker ---------------- */

function DeckPicker({ decks, onPick }: { decks: Deck[]; onPick: (id: string) => void }) {
  const all = decks.find((d) => d.id === DECK_ALL);
  const topics = decks.filter((d) => d.id !== DECK_ALL);

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-6">
        <h1 className="text-2xl font-extrabold tracking-tight">Flashcards</h1>
        <p className="mt-1 text-sm text-slate-400">
          Learn the terms, concepts, and commands behind NKP. Self-graded, so nothing here
          affects your XP or the leaderboard — just practice.
        </p>
      </div>

      {all && (
        <button
          onClick={() => onPick(all.id)}
          className="card mb-6 flex w-full items-center justify-between gap-4 p-5 text-left transition-all hover:border-iris hover:shadow-glow"
        >
          <div className="flex items-center gap-4">
            <Icon name={all.icon} className="text-2xl" />
            <div>
              <div className="text-lg font-bold">{all.title}</div>
              <div className="text-sm text-slate-400">{all.summary}</div>
            </div>
          </div>
          <span className="chip shrink-0 border-iris/40 text-iris-light">{all.count} cards</span>
        </button>
      )}

      <h2 className="mb-2 text-xs font-semibold uppercase tracking-widest text-slate-500">
        By topic
      </h2>
      <div className="grid gap-3 sm:grid-cols-2">
        {topics.map((d) => (
          <button
            key={d.id}
            onClick={() => onPick(d.id)}
            className="card flex flex-col p-4 text-left transition-all hover:border-iris"
          >
            <div className="flex items-center justify-between gap-3">
              <span className="flex items-center gap-2 font-semibold">
                <Icon name={d.icon} />
                {d.title}
              </span>
              <span className="chip shrink-0">{d.count}</span>
            </div>
            <p className="mt-1.5 text-sm leading-snug text-slate-400">{d.summary}</p>
          </button>
        ))}
      </div>
    </div>
  );
}

/* ---------------- Card ---------------- */

function Card({ card, flipped, onFlip }: { card: Flashcard; flipped: boolean; onFlip: () => void }) {
  return (
    <div className="[perspective:1600px]">
      <button
        onClick={onFlip}
        aria-label={flipped ? "Show question" : "Show answer"}
        className={`relative block h-[26rem] w-full text-left transition-transform duration-500 [transform-style:preserve-3d] ${
          flipped ? "[transform:rotateY(180deg)]" : ""
        }`}
      >
        {/* Front — the term or question */}
        <div className="card absolute inset-0 flex flex-col justify-center p-8 [backface-visibility:hidden]">
          <div className="mb-4">
            <span className={`chip ${KIND_STYLES[card.kind]}`}>{card.kind}</span>
          </div>
          <p className="text-2xl font-semibold leading-snug text-slate-50 md:text-3xl">
            <RichText text={card.front} />
          </p>
          <div className="absolute inset-x-0 bottom-6 text-center text-sm text-slate-500">
            See answer
          </div>
        </div>

        {/* Back — the answer, then optional colour (detail), the command itself
            (code), and where in the guide to read more (ref). */}
        <div className="card absolute inset-0 flex flex-col justify-center overflow-y-auto p-8 [backface-visibility:hidden] [transform:rotateY(180deg)]">
          <p className="text-lg font-semibold leading-snug text-slate-50 md:text-xl">
            <RichText text={card.back} />
          </p>

          {card.code && (
            <pre className="mt-4 overflow-x-auto rounded-lg border border-charcoal-border bg-charcoal px-4 py-3 text-left text-xs leading-relaxed text-iris-light">
              <code>{card.code}</code>
            </pre>
          )}

          {card.detail && (
            <p className="mt-4 text-sm leading-relaxed text-slate-400">
              <RichText text={card.detail} />
            </p>
          )}

          {card.ref && <div className="mt-4 text-xs text-slate-600">{card.ref}</div>}
        </div>
      </button>
    </div>
  );
}

/* ---------------- Session ---------------- */

function Session({ deck, onExit }: { deck: FlashcardDeck; onExit: () => void }) {
  const [order, setOrder] = useState<Flashcard[]>(deck.cards);
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [marks, setMarks] = useState<Record<string, Mark>>({});

  const card = order[index];
  const total = order.length;
  const known = useMemo(() => Object.values(marks).filter((m) => m === "known").length, [marks]);
  const unknown = useMemo(
    () => Object.values(marks).filter((m) => m === "unknown").length,
    [marks],
  );
  const done = Object.keys(marks).length === total && total > 0;

  const go = useCallback(
    (delta: number) => {
      setFlipped(false);
      setIndex((i) => Math.min(Math.max(i + delta, 0), total - 1));
    },
    [total],
  );

  /** Mark the current card and advance — the main review loop. */
  const mark = useCallback(
    (m: Mark) => {
      if (!card) return;
      setMarks((prev) => ({ ...prev, [card.id]: m }));
      if (index < total - 1) go(1);
      else setFlipped(false);
    },
    [card, index, total, go],
  );

  // Space flips, arrows navigate. Ignored while typing in a field.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      if (el && ["INPUT", "TEXTAREA"].includes(el.tagName)) return;
      if (e.code === "Space") {
        e.preventDefault(); // stop the page scrolling
        setFlipped((f) => !f);
      } else if (e.key === "ArrowRight") {
        go(1);
      } else if (e.key === "ArrowLeft") {
        go(-1);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [go]);

  function restart(cards: Flashcard[]) {
    setOrder(cards);
    setIndex(0);
    setFlipped(false);
    setMarks({});
  }

  if (!card) {
    return (
      <div className="mx-auto max-w-3xl text-center">
        <p className="text-slate-400">This deck has no cards.</p>
        <button onClick={onExit} className="btn-ghost mt-4">
          Pick another deck
        </button>
      </div>
    );
  }

  const missed = order.filter((c) => marks[c.id] === "unknown");

  return (
    <div className="mx-auto max-w-3xl">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <button onClick={onExit} className="text-sm text-slate-400 hover:text-white">
          ← All decks
        </button>
        <div className="flex items-center gap-2">
          <span className="chip">{deck.title}</span>
          <button
            onClick={() => restart(shuffled(order))}
            className="btn-ghost px-3 py-1.5 text-xs"
          >
            🔀 Shuffle
          </button>
        </div>
      </div>

      {/* Progress */}
      <div className="mb-2 flex items-center justify-between text-xs text-slate-500">
        <span className="font-semibold tabular-nums">
          {index + 1} / {total}
        </span>
        <span>Press “Space” to flip · “←/→” to navigate</span>
      </div>
      <div className="mb-5 h-1 w-full overflow-hidden rounded-full bg-charcoal-light">
        <div
          className="h-full rounded-full bg-gradient-to-r from-iris to-iris-light transition-all duration-300"
          style={{ width: `${((index + 1) / total) * 100}%` }}
        />
      </div>

      <Card card={card} flipped={flipped} onFlip={() => setFlipped((f) => !f)} />

      {/* Controls: back · didn't know · knew it · forward */}
      <div className="mt-6 flex items-center justify-center gap-4">
        <button
          onClick={() => go(-1)}
          disabled={index === 0}
          aria-label="Previous card"
          className="btn-ghost h-12 w-12 rounded-full p-0 text-lg"
        >
          ←
        </button>

        <button
          onClick={() => mark("unknown")}
          aria-label="I didn't know this"
          className={`btn h-12 min-w-[5rem] gap-2 rounded-full border text-base ${
            marks[card.id] === "unknown"
              ? "border-rose-500 bg-rose-500/15 text-rose-300"
              : "border-charcoal-border text-slate-300 hover:border-rose-500/60 hover:text-rose-300"
          }`}
        >
          <span className="text-rose-400">✕</span>
          <span className="tabular-nums">{unknown}</span>
        </button>

        <button
          onClick={() => mark("known")}
          aria-label="I knew this"
          className={`btn h-12 min-w-[5rem] gap-2 rounded-full border text-base ${
            marks[card.id] === "known"
              ? "border-emerald-500 bg-emerald-500/15 text-emerald-300"
              : "border-charcoal-border text-slate-300 hover:border-emerald-500/60 hover:text-emerald-300"
          }`}
        >
          <span className="tabular-nums">{known}</span>
          <span className="text-emerald-400">✓</span>
        </button>

        <button
          onClick={() => go(1)}
          disabled={index === total - 1}
          aria-label="Next card"
          className="btn h-12 w-12 rounded-full border border-iris p-0 text-lg text-iris-light hover:bg-iris/10"
        >
          →
        </button>
      </div>

      {/* End-of-deck summary */}
      {done && (
        <div className="card mt-6 animate-pop p-5 text-center">
          <div className="text-lg font-bold">
            Deck complete — {known}/{total} known
          </div>
          <p className="mt-1 text-sm text-slate-400">
            {missed.length
              ? `${missed.length} card${missed.length === 1 ? "" : "s"} to review.`
              : "Perfect run. Nice."}
          </p>
          <div className="mt-4 flex justify-center gap-3">
            {missed.length > 0 && (
              <button onClick={() => restart(missed)} className="btn-primary">
                Review {missed.length} missed
              </button>
            )}
            <button onClick={() => restart(shuffled(deck.cards))} className="btn-ghost">
              Restart shuffled
            </button>
          </div>
        </div>
      )}

      <p className="mt-6 text-center text-xs text-slate-600">
        Self-graded practice — flashcards don’t award XP.{" "}
        <Link to="/" className="underline hover:text-slate-400">
          Take the quiz
        </Link>{" "}
        to earn XP and badges.
      </p>
    </div>
  );
}

/* ---------------- Page ---------------- */

export default function Flashcards() {
  const [params, setParams] = useSearchParams();
  const deckId = params.get("deck");
  const [decks, setDecks] = useState<Deck[] | null>(null);
  const [deck, setDeck] = useState<FlashcardDeck | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.decks().then(setDecks);
  }, []);

  useEffect(() => {
    if (!deckId) {
      setDeck(null);
      return;
    }
    setLoading(true);
    api
      .flashcards(deckId)
      .then(setDeck)
      .finally(() => setLoading(false));
  }, [deckId]);

  if (loading || (deckId && !deck)) return <Spinner />;
  if (deck) return <Session deck={deck} onExit={() => setParams({})} />;
  if (!decks) return <Spinner />;
  return <DeckPicker decks={decks} onPick={(id) => setParams({ deck: id })} />;
}
