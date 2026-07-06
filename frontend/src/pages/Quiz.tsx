import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { DifficultyTag, Icon, SourceCite, Spinner } from "../components/ui";
import { api } from "../lib/api";
import type { Badge, GradeResult, ModuleDetail } from "../lib/types";

export default function Quiz() {
  const { moduleId } = useParams<{ moduleId: string }>();
  const [module, setModule] = useState<ModuleDetail | null>(null);
  const [index, setIndex] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [result, setResult] = useState<GradeResult | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [earnedXp, setEarnedXp] = useState(0);
  const [toast, setToast] = useState<Badge[] | null>(null);

  useEffect(() => {
    if (!moduleId) return;
    setLoading(true);
    api
      .module(moduleId)
      .then(setModule)
      .finally(() => setLoading(false));
  }, [moduleId]);

  const question = module?.questions[index];
  const isLast = module ? index === module.questions.length - 1 : false;
  const answered = result !== null;

  const typeLabel = useMemo(() => {
    switch (question?.type) {
      case "true_false":
        return "True / False";
      case "scenario":
        return "Scenario";
      default:
        return "Multiple Choice";
    }
  }, [question]);

  async function submit() {
    if (!module || !question || !selected) return;
    setSubmitting(true);
    try {
      const res = await api.answer(module.id, question.id, [selected]);
      setResult(res);
      setEarnedXp((x) => x + res.points_awarded);
      if (res.new_badges.length) {
        setToast(res.new_badges);
        setTimeout(() => setToast(null), 5000);
      }
    } finally {
      setSubmitting(false);
    }
  }

  function next() {
    setSelected(null);
    setResult(null);
    setIndex((i) => i + 1);
  }

  if (loading || !module || !question) return <Spinner />;

  const progressPct = Math.round(((index + (answered ? 1 : 0)) / module.questions.length) * 100);

  // End-of-module summary.
  if (index >= module.questions.length) {
    return <div />;
  }

  return (
    <div className="mx-auto max-w-3xl">
      {/* Badge toast */}
      {toast && (
        <div className="fixed right-5 top-20 z-30 animate-pop">
          {toast.map((b) => (
            <div
              key={b.id}
              className="mb-2 flex items-center gap-3 rounded-xl border border-iris/50 bg-charcoal-card px-4 py-3 shadow-glow"
            >
              <span className="text-2xl">
                <Icon name={b.icon} />
              </span>
              <div>
                <div className="text-xs font-semibold uppercase tracking-wider text-iris-light">
                  Badge unlocked!
                </div>
                <div className="font-bold">{b.name}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <Link to="/" className="text-sm text-slate-400 hover:text-white">
          ← Back to dashboard
        </Link>
        <div className="chip">
          <Icon name={module.icon} /> {module.title}
        </div>
      </div>

      {/* Progress */}
      <div className="mb-6">
        <div className="mb-1.5 flex justify-between text-xs text-slate-400">
          <span>
            Question {index + 1} of {module.questions.length}
          </span>
          <span className="font-semibold text-iris-light">+{earnedXp} XP this session</span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-charcoal-light">
          <div
            className="h-full rounded-full bg-gradient-to-r from-iris to-iris-light transition-all duration-500"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* Question card */}
      <div className="card p-6 md:p-8">
        <div className="mb-4 flex items-center gap-2">
          <span className="chip border-iris/40 text-iris-light">{typeLabel}</span>
          <DifficultyTag difficulty={question.difficulty} />
          <span className="ml-auto text-sm font-semibold text-slate-400">
            {question.points} XP
          </span>
        </div>

        <h2 className="text-xl font-bold leading-snug">{question.prompt}</h2>

        <div className="mt-6 space-y-3">
          {question.options.map((opt) => {
            const isPicked = selected === opt.id;
            const isCorrect = result?.correct_options.includes(opt.id);
            const showAsCorrect = answered && isCorrect;
            const showAsWrong = answered && isPicked && !isCorrect;

            let cls =
              "border-charcoal-border bg-charcoal-light/50 hover:border-iris/60 hover:bg-charcoal-light";
            if (showAsCorrect) cls = "border-emerald-500/60 bg-emerald-500/10";
            else if (showAsWrong) cls = "border-rose-500/60 bg-rose-500/10";
            else if (isPicked) cls = "border-iris bg-iris/10";

            return (
              <button
                key={opt.id}
                disabled={answered}
                onClick={() => setSelected(opt.id)}
                className={`flex w-full items-center gap-3 rounded-xl border px-4 py-3.5 text-left transition-all disabled:cursor-default ${cls}`}
              >
                <span
                  className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-xs font-bold uppercase ${
                    isPicked || showAsCorrect
                      ? "border-transparent bg-iris text-white"
                      : "border-charcoal-border text-slate-400"
                  }`}
                >
                  {opt.id}
                </span>
                <span className="flex-1">{opt.text}</span>
                {showAsCorrect && <span className="text-emerald-400">✓</span>}
                {showAsWrong && <span className="text-rose-400">✗</span>}
              </button>
            );
          })}
        </div>

        {/* Feedback */}
        {answered && (
          <div
            className={`mt-5 animate-pop rounded-xl border p-4 ${
              result!.correct
                ? "border-emerald-500/40 bg-emerald-500/10"
                : "border-rose-500/40 bg-rose-500/10"
            }`}
          >
            <div className="mb-1 font-bold">
              {result!.correct
                ? `✅ Correct! +${result!.points_awarded} XP`
                : "❌ Not quite."}
            </div>
            <p className="text-sm text-slate-300">{result!.explanation}</p>
            {result!.source && <SourceCite source={result!.source} />}
          </div>
        )}

        {/* Actions */}
        <div className="mt-6 flex justify-end gap-3">
          {!answered ? (
            <button
              onClick={submit}
              disabled={!selected || submitting}
              className="btn-primary"
            >
              {submitting ? "Checking…" : "Submit answer"}
            </button>
          ) : isLast ? (
            <Link to="/" className="btn-primary">
              Finish module →
            </Link>
          ) : (
            <button onClick={next} className="btn-primary">
              Next question →
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
