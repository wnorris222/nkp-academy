import { useMemo, useState } from "react";
import { DifficultyTag, SourceCite, Spinner } from "../components/ui";
import { api } from "../lib/api";
import type { Exam, ExamQuestion, ExamReport } from "../lib/types";

type Phase = "config" | "taking" | "results";

const LENGTHS = [
  { n: 25, label: "Quick", blurb: "~15 min warm-up" },
  { n: 50, label: "Standard", blurb: "~30 min, exam-like" },
  { n: 75, label: "Full", blurb: "~45 min, full sweep" },
];

const key = (q: { module_id: string; question_id: string }) =>
  `${q.module_id}:${q.question_id}`;

export default function ExamPage() {
  const [phase, setPhase] = useState<Phase>("config");
  const [exam, setExam] = useState<Exam | null>(null);
  const [answers, setAnswers] = useState<Record<string, string[]>>({});
  const [index, setIndex] = useState(0);
  const [report, setReport] = useState<ExamReport | null>(null);
  const [busy, setBusy] = useState(false);

  async function start(count: number) {
    setBusy(true);
    try {
      const e = await api.generateExam(count);
      setExam(e);
      setAnswers({});
      setIndex(0);
      setReport(null);
      setPhase("taking");
    } finally {
      setBusy(false);
    }
  }

  function toggle(q: ExamQuestion, optId: string) {
    setAnswers((prev) => {
      const cur = prev[key(q)] ?? [];
      let next: string[];
      if (q.multiple) {
        next = cur.includes(optId) ? cur.filter((x) => x !== optId) : [...cur, optId];
      } else {
        next = [optId];
      }
      return { ...prev, [key(q)]: next };
    });
  }

  async function submit() {
    if (!exam) return;
    setBusy(true);
    try {
      const payload = exam.questions.map((q) => ({
        module_id: q.module_id,
        question_id: q.question_id,
        selected: answers[key(q)] ?? [],
      }));
      const r = await api.submitExam(payload);
      setReport(r);
      setPhase("results");
      window.scrollTo(0, 0);
    } finally {
      setBusy(false);
    }
  }

  if (phase === "config") return <ExamConfig busy={busy} onStart={start} />;
  if (phase === "taking" && exam)
    return (
      <ExamRunner
        exam={exam}
        answers={answers}
        index={index}
        setIndex={setIndex}
        onToggle={toggle}
        onSubmit={submit}
        busy={busy}
      />
    );
  if (phase === "results" && exam && report)
    return (
      <ExamResults
        exam={exam}
        report={report}
        answers={answers}
        onRetake={() => setPhase("config")}
      />
    );
  return <Spinner />;
}

// ---- Config screen ----

function ExamConfig({
  busy,
  onStart,
}: {
  busy: boolean;
  onStart: (n: number) => void;
}) {
  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-extrabold tracking-tight md:text-3xl">
        📝 Practice Exam
      </h1>
      <p className="mt-2 text-slate-400">
        A timed-style mock exam that pulls questions from <strong>every NCP-CN
        section</strong> so you can gauge your readiness without grinding each
        module. No instant feedback — you'll get a scored report with a
        section-by-section breakdown at the end. This doesn't affect your XP or
        the leaderboard.
      </p>

      <h2 className="mt-8 mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
        Choose a length
      </h2>
      <div className="grid gap-4 sm:grid-cols-3">
        {LENGTHS.map((l) => (
          <button
            key={l.n}
            disabled={busy}
            onClick={() => onStart(l.n)}
            className="card group flex flex-col items-start p-5 text-left transition-all hover:-translate-y-0.5 hover:border-iris hover:shadow-glow disabled:opacity-50"
          >
            <span className="text-3xl font-extrabold text-iris-light">{l.n}</span>
            <span className="mt-1 font-bold">{l.label}</span>
            <span className="text-xs text-slate-400">{l.blurb}</span>
          </button>
        ))}
      </div>
      <p className="mt-6 text-sm text-slate-500">
        Passing score: <strong className="text-slate-300">75%</strong>. Questions
        are drawn randomly and balanced across sections, so every exam is
        different.
      </p>
    </div>
  );
}

// ---- Runner (taking the exam) ----

function ExamRunner({
  exam,
  answers,
  index,
  setIndex,
  onToggle,
  onSubmit,
  busy,
}: {
  exam: Exam;
  answers: Record<string, string[]>;
  index: number;
  setIndex: (n: number) => void;
  onToggle: (q: ExamQuestion, optId: string) => void;
  onSubmit: () => void;
  busy: boolean;
}) {
  const q = exam.questions[index];
  const selected = answers[key(q)] ?? [];
  const answeredCount = exam.questions.filter(
    (qq) => (answers[key(qq)] ?? []).length > 0,
  ).length;
  const isLast = index === exam.questions.length - 1;

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-lg font-bold">Practice Exam</h1>
        <span className="chip">
          {answeredCount}/{exam.questions.length} answered
        </span>
      </div>

      {/* Question navigator */}
      <div className="mb-5 flex flex-wrap gap-1.5">
        {exam.questions.map((qq, i) => {
          const done = (answers[key(qq)] ?? []).length > 0;
          const current = i === index;
          return (
            <button
              key={key(qq)}
              onClick={() => setIndex(i)}
              className={`h-7 w-7 rounded-md text-xs font-semibold transition-colors ${
                current
                  ? "bg-iris text-white"
                  : done
                    ? "bg-iris/25 text-iris-light"
                    : "bg-charcoal-light text-slate-500 hover:text-slate-300"
              }`}
            >
              {i + 1}
            </button>
          );
        })}
      </div>

      {/* Question card */}
      <div className="card p-6 md:p-8">
        <div className="mb-4 flex items-center gap-2">
          <span className="chip border-iris/40 text-iris-light">{q.track}</span>
          <DifficultyTag difficulty={q.difficulty} />
          {q.multiple && (
            <span className="chip border-amber-500/40 text-amber-300">
              Select all that apply
            </span>
          )}
          <span className="ml-auto text-sm text-slate-500">
            {index + 1} / {exam.questions.length}
          </span>
        </div>

        <h2 className="text-xl font-bold leading-snug">{q.prompt}</h2>

        <div className="mt-6 space-y-3">
          {q.options.map((opt) => {
            const picked = selected.includes(opt.id);
            return (
              <button
                key={opt.id}
                onClick={() => onToggle(q, opt.id)}
                className={`flex w-full items-center gap-3 rounded-xl border px-4 py-3.5 text-left transition-all ${
                  picked
                    ? "border-iris bg-iris/10"
                    : "border-charcoal-border bg-charcoal-light/50 hover:border-iris/60 hover:bg-charcoal-light"
                }`}
              >
                <span
                  className={`flex h-6 w-6 shrink-0 items-center justify-center border text-xs font-bold uppercase ${
                    q.multiple ? "rounded-md" : "rounded-full"
                  } ${
                    picked
                      ? "border-transparent bg-iris text-white"
                      : "border-charcoal-border text-slate-400"
                  }`}
                >
                  {opt.id}
                </span>
                <span className="flex-1">{opt.text}</span>
              </button>
            );
          })}
        </div>

        <div className="mt-6 flex items-center justify-between gap-3">
          <button
            onClick={() => setIndex(Math.max(0, index - 1))}
            disabled={index === 0}
            className="btn-ghost"
          >
            ← Previous
          </button>
          {!isLast ? (
            <button onClick={() => setIndex(index + 1)} className="btn-primary">
              Next →
            </button>
          ) : (
            <button onClick={onSubmit} disabled={busy} className="btn-primary">
              {busy ? "Scoring…" : "Submit exam"}
            </button>
          )}
        </div>
      </div>

      {/* Persistent submit for early finishers */}
      {!isLast && (
        <div className="mt-4 text-center">
          <button
            onClick={onSubmit}
            disabled={busy}
            className="text-sm text-slate-400 underline-offset-4 hover:text-white hover:underline"
          >
            {busy ? "Scoring…" : `Finish & submit now (${answeredCount}/${exam.questions.length} answered)`}
          </button>
        </div>
      )}
    </div>
  );
}

// ---- Results ----

function ExamResults({
  exam,
  report,
  answers,
  onRetake,
}: {
  exam: Exam;
  report: ExamReport;
  answers: Record<string, string[]>;
  onRetake: () => void;
}) {
  const pct = Math.round(report.score_pct * 100);
  const resultByKey = useMemo(() => {
    const m = new Map<string, ExamReport["results"][number]>();
    report.results.forEach((r) => m.set(`${r.module_id}:${r.question_id}`, r));
    return m;
  }, [report]);

  return (
    <div className="mx-auto max-w-3xl">
      {/* Scorecard */}
      <div
        className={`card overflow-hidden border-2 p-8 text-center ${
          report.passed ? "border-emerald-500/50" : "border-rose-500/50"
        }`}
      >
        <div
          className={`text-6xl font-extrabold ${
            report.passed ? "text-emerald-400" : "text-rose-400"
          }`}
        >
          {pct}%
        </div>
        <div
          className={`mt-2 inline-block rounded-full px-4 py-1 text-sm font-bold uppercase tracking-wider ${
            report.passed
              ? "bg-emerald-500/15 text-emerald-300"
              : "bg-rose-500/15 text-rose-300"
          }`}
        >
          {report.passed ? "Passed 🎉" : "Not yet — keep studying"}
        </div>
        <p className="mt-3 text-slate-400">
          {report.correct} of {report.total} correct · passing score{" "}
          {Math.round(report.pass_threshold * 100)}%
        </p>
        <button onClick={onRetake} className="btn-primary mt-6">
          Take another exam
        </button>
      </div>

      {/* Section breakdown */}
      <h2 className="mb-3 mt-8 text-lg font-bold">Section breakdown</h2>
      <div className="card divide-y divide-charcoal-border">
        {report.sections.map((s) => {
          const spct = s.total ? Math.round((s.correct / s.total) * 100) : 0;
          return (
            <div key={s.track} className="flex items-center gap-4 px-5 py-3.5">
              <div className="w-40 shrink-0 truncate text-sm font-semibold">
                {s.track}
              </div>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-charcoal-light">
                <div
                  className={`h-full rounded-full ${
                    spct >= 75 ? "bg-emerald-500" : spct >= 50 ? "bg-amber-500" : "bg-rose-500"
                  }`}
                  style={{ width: `${spct}%` }}
                />
              </div>
              <div className="w-20 shrink-0 text-right text-sm text-slate-400">
                {s.correct}/{s.total} · {spct}%
              </div>
            </div>
          );
        })}
      </div>

      {/* Answer review */}
      <h2 className="mb-3 mt-8 text-lg font-bold">Review answers</h2>
      <div className="space-y-3">
        {exam.questions.map((q, i) => {
          const r = resultByKey.get(key(q));
          const picked = answers[key(q)] ?? [];
          const correctSet = new Set(r?.correct_options ?? []);
          return (
            <div key={key(q)} className="card p-5">
              <div className="mb-2 flex items-start gap-2">
                <span
                  className={`mt-0.5 shrink-0 text-sm font-bold ${
                    r?.correct ? "text-emerald-400" : "text-rose-400"
                  }`}
                >
                  {r?.correct ? "✓" : "✗"}
                </span>
                <div className="min-w-0">
                  <div className="text-xs text-slate-500">
                    Q{i + 1} · {q.track}
                  </div>
                  <div className="font-semibold">{q.prompt}</div>
                </div>
              </div>
              <div className="mt-2 space-y-1.5 pl-6">
                {q.options.map((opt) => {
                  const isCorrect = correctSet.has(opt.id);
                  const isPicked = picked.includes(opt.id);
                  return (
                    <div
                      key={opt.id}
                      className={`flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm ${
                        isCorrect
                          ? "bg-emerald-500/10 text-emerald-200"
                          : isPicked
                            ? "bg-rose-500/10 text-rose-200"
                            : "text-slate-400"
                      }`}
                    >
                      <span className="font-bold uppercase">{opt.id}</span>
                      <span className="flex-1">{opt.text}</span>
                      {isCorrect && <span className="text-emerald-400">correct</span>}
                      {isPicked && !isCorrect && (
                        <span className="text-rose-400">your pick</span>
                      )}
                    </div>
                  );
                })}
              </div>
              {r?.explanation && (
                <p className="mt-2 pl-6 text-sm text-slate-400">{r.explanation}</p>
              )}
              {r?.source && (
                <div className="pl-6">
                  <SourceCite source={r.source} />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
