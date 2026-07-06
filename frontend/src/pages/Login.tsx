import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(username.trim(), displayName.trim() || undefined);
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-5">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-charcoal-light shadow-glow">
            <svg viewBox="0 0 64 64" className="h-10 w-10">
              <path
                d="M16 44V20l16 12 16-12v24"
                fill="none"
                stroke="#7855FA"
                strokeWidth="6"
                strokeLinejoin="round"
                strokeLinecap="round"
              />
            </svg>
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight">NKP Academy</h1>
          <p className="mt-2 text-slate-400">
            Level up your Nutanix Kubernetes Platform expertise. Earn XP, unlock
            badges, top the leaderboard.
          </p>
        </div>

        <form onSubmit={onSubmit} className="card space-y-4 p-6">
          <div>
            <label className="mb-1.5 block text-sm font-semibold text-slate-300">
              Username
            </label>
            <input
              autoFocus
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. priya-partner"
              className="w-full rounded-xl border border-charcoal-border bg-charcoal-light px-4 py-2.5 text-slate-100 outline-none focus:border-iris"
              required
              minLength={2}
            />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-semibold text-slate-300">
              Display name <span className="text-slate-500">(optional)</span>
            </label>
            <input
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Priya (Acme Cloud)"
              className="w-full rounded-xl border border-charcoal-border bg-charcoal-light px-4 py-2.5 text-slate-100 outline-none focus:border-iris"
            />
          </div>

          {error && (
            <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-2.5 text-sm text-rose-300">
              {error}
            </div>
          )}

          <button type="submit" disabled={busy} className="btn-primary w-full">
            {busy ? "Starting…" : "Start learning"}
          </button>
          <p className="text-center text-xs text-slate-500">
            No password needed — this is a partner enablement sandbox. SSO/OIDC
            can be enabled by your Nutanix admin.
          </p>
        </form>
      </div>
    </div>
  );
}
