// Thin typed API client. Same-origin in production; Vite proxies /api in dev.
import type {
  Badge,
  Exam,
  ExamAnswerInput,
  ExamReport,
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

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["X-Session-Token"] = token;

  const resp = await fetch(path, { ...options, headers });
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      detail = (await resp.json()).detail ?? detail;
    } catch {
      /* ignore non-JSON errors */
    }
    throw new ApiError(resp.status, detail);
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
  generateExam: (count: number) => request<Exam>(`/api/exam?count=${count}`),
  submitExam: (answers: ExamAnswerInput[]) =>
    request<ExamReport>("/api/exam/submit", {
      method: "POST",
      body: JSON.stringify({ answers }),
    }),
};
