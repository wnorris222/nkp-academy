import { useEffect, useState } from "react";
import { Spinner } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { Leaderboard as LeaderboardData } from "../lib/types";

const MEDALS = ["🥇", "🥈", "🥉"];

export default function Leaderboard() {
  const { user } = useAuth();
  const [data, setData] = useState<LeaderboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .leaderboard()
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  if (loading || !data) return <Spinner />;

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-extrabold tracking-tight md:text-3xl">
        🏆 Leaderboard
      </h1>
      <p className="mt-1 text-slate-400">
        The top NKP partners by XP. Complete modules and ace quizzes to climb.
      </p>

      <div className="card mt-6 divide-y divide-charcoal-border">
        {data.entries.length === 0 && (
          <div className="p-8 text-center text-slate-500">
            No scores yet — be the first to earn XP!
          </div>
        )}
        {data.entries.map((e) => {
          const isMe = e.username === user?.username;
          return (
            <div
              key={e.username}
              className={`flex items-center gap-4 px-5 py-4 ${
                isMe ? "bg-iris/10" : ""
              }`}
            >
              <div className="w-8 text-center text-lg font-bold">
                {e.rank <= 3 ? MEDALS[e.rank - 1] : <span className="text-slate-500">{e.rank}</span>}
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-iris/20 font-bold text-iris-light">
                {e.display_name.charAt(0).toUpperCase()}
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate font-semibold">
                  {e.display_name}
                  {isMe && <span className="ml-2 text-xs text-iris-light">(you)</span>}
                </div>
                <div className="text-xs text-slate-500">
                  Level {e.level} · {e.badge_count} badge{e.badge_count === 1 ? "" : "s"}
                </div>
              </div>
              <div className="text-right">
                <div className="text-lg font-extrabold text-iris-light">{e.total_xp}</div>
                <div className="text-[11px] uppercase tracking-wider text-slate-500">XP</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
