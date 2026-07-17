"""Pydantic request/response schemas (the API contract)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

# ---- Content (safe projections that never leak correct answers) ----

class OptionOut(BaseModel):
    id: str
    text: str


class QuestionOut(BaseModel):
    id: str
    type: str
    prompt: str
    options: list[OptionOut]
    points: int
    difficulty: str
    # True when more than one option is correct ("select all that apply"). Lets
    # the client render checkboxes; it does not reveal which options are correct.
    multiple: bool = False
    # Correct answers/explanation are intentionally omitted here; they are only
    # returned in the grade response after the user submits.


class ModuleSummaryOut(BaseModel):
    id: str
    title: str
    track: str
    order: int
    summary: str
    icon: str
    question_count: int
    total_points: int


class ModuleDetailOut(ModuleSummaryOut):
    questions: list[QuestionOut]


class BadgeOut(BaseModel):
    id: str
    name: str
    description: str
    icon: str


# ---- Auth ----

class LoginRequest(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    display_name: str | None = Field(default=None, max_length=128)

    @field_validator("username")
    @classmethod
    def _slug(cls, v: str) -> str:
        v = v.strip().lower()
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("username may contain only letters, numbers, - and _")
        return v


class UserOut(BaseModel):
    id: int
    username: str
    display_name: str
    token: str  # opaque session token (the username today; OIDC later)


# ---- Quiz ----

class AnswerSubmission(BaseModel):
    question_id: str
    selected: list[str] = Field(min_length=1)


class SourceOut(BaseModel):
    label: str
    url: str
    page: str = ""
    quote: str = ""
    label2: str = ""
    url2: str = ""


class GradeOut(BaseModel):
    question_id: str
    correct: bool
    points_awarded: int
    correct_options: list[str]
    explanation: str
    source: SourceOut | None = None
    total_xp: int
    level: int
    xp_to_next_level: int
    new_badges: list[BadgeOut] = []


# ---- Progress ----

class ModuleProgressOut(BaseModel):
    module_id: str
    questions_answered: int
    questions_correct: int
    xp_earned: int
    completed: bool


class ProgressOut(BaseModel):
    username: str
    display_name: str
    total_xp: int
    level: int
    xp_to_next_level: int
    modules: list[ModuleProgressOut]
    badges: list[BadgeOut]


# ---- Leaderboard ----

class LeaderboardEntry(BaseModel):
    rank: int
    username: str
    display_name: str
    total_xp: int
    level: int
    badge_count: int


class LeaderboardOut(BaseModel):
    entries: list[LeaderboardEntry]
    generated_at: datetime


# ---- Flashcards ----

class FlashcardOut(BaseModel):
    id: str
    module_id: str
    module_title: str
    track: str
    front: str
    answer: str
    back: str
    source: SourceOut | None = None


class DeckOut(BaseModel):
    id: str
    title: str
    kind: str  # "all" | "track" | "module"
    count: int


class FlashcardDeckOut(BaseModel):
    deck_id: str
    title: str
    count: int
    cards: list[FlashcardOut]


# ---- Practice exam ----

class ExamQuestionOut(BaseModel):
    module_id: str
    module_title: str
    track: str
    question_id: str
    type: str
    prompt: str
    options: list[OptionOut]
    points: int
    difficulty: str
    # True when more than one option is correct ("select all that apply").
    # Lets the client render checkboxes; it does not reveal which options.
    multiple: bool


class ExamOut(BaseModel):
    count: int
    pass_threshold: float
    questions: list[ExamQuestionOut]


class ExamAnswer(BaseModel):
    module_id: str
    question_id: str
    selected: list[str] = []  # empty = unanswered (graded incorrect)


class ExamSubmitRequest(BaseModel):
    answers: list[ExamAnswer] = Field(min_length=1)


class ExamQuestionResultOut(BaseModel):
    module_id: str
    question_id: str
    track: str
    correct: bool
    correct_options: list[str]
    explanation: str
    source: SourceOut | None = None


class ExamSectionResultOut(BaseModel):
    track: str
    correct: int
    total: int


class ExamReportOut(BaseModel):
    total: int
    answered: int
    correct: int
    score_pct: float
    passed: bool
    pass_threshold: float
    sections: list[ExamSectionResultOut]
    results: list[ExamQuestionResultOut]
