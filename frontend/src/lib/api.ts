// Thin typed API client. Same-origin in production; Vite proxies /api in dev.
import type {
  Badge,
  Deck,
  Exam,
  ExamAnswerInput,
  ExamReport,
  FlashcardDeck,
  GradeResult,
  Leaderboard,
  ModuleDetail,
  ModuleSummary,
  Progress,
  User,
} from "./types";

const TOKEN_KEY = "nkp_academy_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

/** Flatten a FastAPI error body into one readable line.
 *
 * FastAPI uses two shapes: `{detail: "..."}` for a raised HTTPException, and
 * `{detail: [{msg, loc}, ...]}` for 422 request-validation failures. Treating
 * the second as a string renders "[object Object]" and hides the real reason,
 * so both are handled here.
 */
function errorMessage(body: unknown, fallback: string): string {
  const detail = (body as { detail?: unknown } | null)?.detail;

  if (typeof detail === "string" && detail.trim()) return detail;

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (item as { msg?: unknown })?.msg)
      .filter((msg): msg is string => typeof msg === "string" && msg.trim().length > 0)
      // Pydantic prefixes custom-validator failures with "Value error, ".
      .map((msg) => msg.replace(/^value error,\s*/i, ""));
    if (messages.length) return messages.join(" · ");
  }

  return fallback;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["X-Session-Token"] = token;

  const resp = await fetch(path, { ...options, headers });
  if (!resp.ok) {
    let message = resp.statusText;
    try {
      message = errorMessage(await resp.json(), message);
    } catch {
      /* non-JSON error body — keep the status text */
    }
    throw new ApiError(resp.status, message);
  }
  if (resp.status === 204) return undefined as T;
  return resp.json() as Promise<T>;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

export const api = {
  login: (username: string, display_name?: string) =>
    request<User>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, display_name }),
    }),
  me: () => request<User>("/api/auth/me"),
  modules: () => request<ModuleSummary[]>("/api/content/modules"),
  module: (id: string) => request<ModuleDetail>(`/api/content/modules/${id}`),
  badges: () => request<Badge[]>("/api/content/badges"),
  answer: (moduleId: string, questionId: string, selected: string[]) =>
    request<GradeResult>(`/api/quiz/${moduleId}/answer`, {
      method: "POST",
      body: JSON.stringify({ question_id: questionId, selected }),
    }),
  progress: () => request<Progress>("/api/progress"),
  leaderboard: () => request<Leaderboard>("/api/leaderboard"),
  decks: () => request<Deck[]>("/api/flashcards/decks"),
  flashcards: (deckId: string) =>
    request<FlashcardDeck>(`/api/flashcards?deck_id=${encodeURIComponent(deckId)}`),
  generateExam: (count: number) => request<Exam>(`/api/exam?count=${count}`),
  submitExam: (answers: ExamAnswerInput[]) =>
    request<ExamReport>("/api/exam/submit", {
      method: "POST",
      body: JSON.stringify({ answers }),
    }),
};
