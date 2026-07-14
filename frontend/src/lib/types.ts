// Shared API types (mirror backend Pydantic schemas).

export interface User {
  id: number;
  username: string;
  display_name: string;
  token: string;
}

export interface Option {
  id: string;
  text: string;
}

export interface Question {
  id: string;
  type: "multiple_choice" | "true_false" | "scenario";
  prompt: string;
  options: Option[];
  points: number;
  difficulty: string;
  multiple: boolean;
}

export interface ModuleSummary {
  id: string;
  title: string;
  track: string;
  order: number;
  summary: string;
  icon: string;
  question_count: number;
  total_points: number;
}

export interface ModuleDetail extends ModuleSummary {
  questions: Question[];
}

export interface Badge {
  id: string;
  name: string;
  description: string;
  icon: string;
}

export interface Source {
  label: string;
  url: string;
  page: string;
  quote: string;
  label2?: string;
  url2?: string;
}

export interface GradeResult {
  question_id: string;
  correct: boolean;
  points_awarded: number;
  correct_options: string[];
  explanation: string;
  source?: Source | null;
  total_xp: number;
  level: number;
  xp_to_next_level: number;
  new_badges: Badge[];
}

export interface ModuleProgress {
  module_id: string;
  questions_answered: number;
  questions_correct: number;
  xp_earned: number;
  completed: boolean;
}

export interface Progress {
  username: string;
  display_name: string;
  total_xp: number;
  level: number;
  xp_to_next_level: number;
  modules: ModuleProgress[];
  badges: Badge[];
}

export interface LeaderboardEntry {
  rank: number;
  username: string;
  display_name: string;
  total_xp: number;
  level: number;
  badge_count: number;
}

export interface Leaderboard {
  entries: LeaderboardEntry[];
  generated_at: string;
}

export interface ExamQuestion {
  module_id: string;
  module_title: string;
  track: string;
  question_id: string;
  type: "multiple_choice" | "true_false" | "scenario";
  prompt: string;
  options: Option[];
  points: number;
  difficulty: string;
  multiple: boolean;
}

export interface Exam {
  count: number;
  pass_threshold: number;
  questions: ExamQuestion[];
}

export interface ExamAnswerInput {
  module_id: string;
  question_id: string;
  selected: string[];
}

export interface ExamQuestionResult {
  module_id: string;
  question_id: string;
  track: string;
  correct: boolean;
  correct_options: string[];
  explanation: string;
  source?: Source | null;
}

export interface ExamSectionResult {
  track: string;
  correct: number;
  total: number;
}

export interface ExamReport {
  total: number;
  answered: number;
  correct: number;
  score_pct: number;
  passed: boolean;
  pass_threshold: number;
  sections: ExamSectionResult[];
  results: ExamQuestionResult[];
}
