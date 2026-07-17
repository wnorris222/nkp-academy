// App shell: top nav with brand, links, and the current user.
import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../lib/auth";

function BrandMark() {
  return (
    <Link
      to="/"
      aria-label="NKP Academy home"
      className="flex items-center gap-2.5 rounded-lg transition-opacity hover:opacity-80"
    >
      <svg viewBox="0 0 64 64" className="h-8 w-8">
        <rect width="64" height="64" rx="14" fill="#1E1E22" />
        <path
          d="M16 44V20l16 12 16-12v24"
          fill="none"
          stroke="#7855FA"
          strokeWidth="6"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      </svg>
      <div className="leading-tight">
        <div className="font-extrabold tracking-tight">NKP Academy</div>
        <div className="text-[11px] uppercase tracking-widest text-iris-light">
          Partner Enablement
        </div>
      </div>
    </Link>
  );
}

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-lg px-3 py-2 text-sm font-semibold transition-colors ${
    isActive ? "bg-iris/20 text-white" : "text-slate-400 hover:text-white"
  }`;

export default function Layout() {
  const { user, logout } = useAuth();
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-charcoal-border bg-charcoal/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-3">
          <BrandMark />
          <nav className="flex items-center gap-1">
            <NavLink to="/" end className={linkClass}>
              Dashboard
            </NavLink>
            <NavLink to="/flashcards" className={linkClass}>
              Flashcards
            </NavLink>
            <NavLink to="/exam" className={linkClass}>
              Practice Exam
            </NavLink>
            <NavLink to="/leaderboard" className={linkClass}>
              Leaderboard
            </NavLink>
            {user && (
              <div className="ml-3 flex items-center gap-3 border-l border-charcoal-border pl-3">
                <span className="hidden text-sm text-slate-300 sm:inline">
                  {user.display_name}
                </span>
                <button onClick={logout} className="btn-ghost px-3 py-1.5 text-sm">
                  Sign out
                </button>
              </div>
            )}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-5 py-8">
        <Outlet />
      </main>
      <footer className="mx-auto max-w-6xl px-5 py-8 text-center text-xs text-slate-600">
        NKP Academy · Built for Nutanix channel partners · Content sourced from the
        Nutanix Kubernetes Platform 2.17 Guide
      </footer>
    </div>
  );
}
