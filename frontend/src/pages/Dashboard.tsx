import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Icon, Spinner, XpBar } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { Badge, ModuleSummary, Progress } from "../lib/types";

export default function Dashboard() {
  const { user } = useAuth();
  const [modules, setModules] = useState<ModuleSummary[]>([]);
  const [badges, setBadges] = useState<Badge[]>([]);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.modules(), api.badges(), api.progress()])
      .then(([m, b, p]) => {
        setModules(m);
        setBadges(b);
        setProgress(p);
      })
      .finally(() => setLoading(false));
  }, []);

  const progressByModule = useMemo(() => {
    const map = new Map<string, Progress["modules"][number]>();
    progress?.modules.forEach((m) => map.set(m.module_id, m));
    return map;
  }, [progress]);

  const earnedBadgeIds = useMemo(
    () => new Set(progress?.badges.map((b) => b.id)),
    [progress],
  );

  const tracks = useMemo(() => {
    const order: string[] = [];
    modules.forEach((m) => !order.includes(m.track) && order.push(m.track));
    return order.map((t) => ({ track: t, modules: modules.filter((m) => m.track === t) }));
  }, [modules]);

  if (loading || !progress) return <Spinner />;

  const completedCount = progress.modules.filter((m) => m.completed).length;

  return (
    <div className="space-y-8">
      {/* Hero / stats */}
      <section className="card overflow-hidden">
        <div className="grid gap-6 p-6 md:grid-cols-[1.4fr,1fr] md:p-8">
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight md:text-3xl">
              Welcome back, {user?.display_name.split(" ")[0]} 👋
            </h1>
            <p className="mt-1 max-w-lg text-slate-400">
              Master the Nutanix Kubernetes Platform through bite-sized modules.
              Answer questions, earn XP, and unlock badges as you become an NKP pro.
            </p>
            <div className="mt-6 grid grid-cols-3 gap-3">
              <Stat label="Total XP" value={progress.total_xp} accent />
              <Stat label="Level" value={progress.level} />
              <Stat label="Modules done" value={`${completedCount}/${modules.length}`} />
            </div>
          </div>
          <div className="flex flex-col justify-center rounded-xl border border-charcoal-border bg-charcoal-light/60 p-5">
            <XpBar
              level={progress.level}
              total={progress.total_xp}
              toNext={progress.xp_to_next_level}
            />
          </div>
        </div>
      </section>

      {/* Practice exam CTA */}
      <Link
        to="/exam"
        className="card group flex items-center gap-4 border-iris/30 bg-gradient-to-r from-iris/15 to-transparent p-5 transition-all hover:border-iris hover:shadow-glow"
      >
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-iris/20 text-2xl">
          📝
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="font-bold group-hover:text-iris-light">
            Take a Practice Exam
          </h3>
          <p className="text-sm text-slate-400">
            Test yourself with questions pulled from every section — get a scored
            report and see where to focus before the real exam.
          </p>
        </div>
        <span className="hidden shrink-0 text-iris-light sm:inline">→</span>
      </Link>

      {/* Tracks & modules */}
      {tracks.map(({ track, modules: mods }) => (
        <section key={track}>
          <h2 className="mb-3 flex items-center gap-2 text-lg font-bold">
            <span className="h-4 w-1.5 rounded-full bg-iris" />
            {track}
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {mods.map((m) => {
              const p = progressByModule.get(m.id);
              const done = p?.questions_correct ?? 0;
              const pct = Math.round((done / m.question_count) * 100);
              return (
                <Link
                  key={m.id}
                  to={`/module/${m.id}`}
                  className="card group flex flex-col p-5 transition-all hover:-translate-y-0.5 hover:border-iris hover:shadow-glow"
                >
                  <div className="mb-3 flex items-start justify-between">
                    <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-iris/15 text-xl">
                      <Icon name={m.icon} />
                    </div>
                    {p?.completed && (
                      <span className="chip border-emerald-500/40 text-emerald-300">
                        ✓ Complete
                      </span>
                    )}
                  </div>
                  <h3 className="font-bold group-hover:text-iris-light">{m.title}</h3>
                  <p className="mt-1 flex-1 text-sm text-slate-400 line-clamp-3">
                    {m.summary}
                  </p>
                  <div className="mt-4">
                    <div className="mb-1 flex justify-between text-xs text-slate-400">
                      <span>
                        {done}/{m.question_count} correct
                      </span>
                      <span>{m.total_points} XP</span>
                    </div>
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-charcoal-light">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-iris to-iris-light transition-all"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        </section>
      ))}

      {/* Badges */}
      <section>
        <h2 className="mb-3 flex items-center gap-2 text-lg font-bold">
          <span className="h-4 w-1.5 rounded-full bg-iris" />
          Badges
          <span className="text-sm font-normal text-slate-500">
            {earnedBadgeIds.size}/{badges.length} earned
          </span>
        </h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {badges.map((b) => {
            const earned = earnedBadgeIds.has(b.id);
            return (
              <div
                key={b.id}
                className={`card flex items-center gap-3 p-4 ${
                  earned ? "" : "opacity-45 grayscale"
                }`}
                title={b.description}
              >
                <div className="text-2xl">
                  <Icon name={b.icon} />
                </div>
                <div className="min-w-0">
                  <div className="truncate text-sm font-bold">{b.name}</div>
                  <div className="truncate text-xs text-slate-400">{b.description}</div>
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}

function Stat({
  label,
  value,
  accent = false,
}: {
  label: string;
  value: string | number;
  accent?: boolean;
}) {
  return (
    <div className="rounded-xl border border-charcoal-border bg-charcoal-light/60 p-3 text-center">
      <div className={`text-2xl font-extrabold ${accent ? "text-iris-light" : ""}`}>
        {value}
      </div>
      <div className="text-[11px] uppercase tracking-wider text-slate-500">{label}</div>
    </div>
  );
}
