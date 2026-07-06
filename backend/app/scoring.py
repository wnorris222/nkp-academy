"""Pure quiz-scoring, XP, and badge logic.

Deliberately free of I/O and database access so it is trivially unit-testable
and reusable. Routers call these functions and then persist the results.
"""
from __future__ import annotations

from dataclasses import dataclass

from .content import Badge, ContentStore, Module, Question


@dataclass(frozen=True)
class GradedAnswer:
    """Result of grading a single answered question."""

    question_id: str
    correct: bool
    points_awarded: int
    correct_options: tuple[str, ...]
    explanation: str


def grade_answer(question: Question, selected: list[str]) -> GradedAnswer:
    """Grade a submission against a question.

    An answer is correct only when the set of selected option ids exactly
    matches the question's correct set — this handles single-answer
    (multiple choice, true/false, scenario) and multi-select uniformly.
    Full points on a correct answer, zero otherwise (no partial credit).
    """
    chosen = frozenset(selected)
    is_correct = chosen == question.correct_set
    points = question.points if is_correct else 0
    return GradedAnswer(
        question_id=question.id,
        correct=is_correct,
        points_awarded=points,
        correct_options=tuple(sorted(question.correct_set)),
        explanation=question.explanation,
    )


@dataclass(frozen=True)
class ModuleScore:
    module_id: str
    answered: int
    correct: int
    xp: int
    total_questions: int
    completed: bool

    @property
    def accuracy(self) -> float:
        return (self.correct / self.answered) if self.answered else 0.0


def score_module(
    module: Module,
    graded: list[GradedAnswer],
) -> ModuleScore:
    """Aggregate graded answers for one module into a progress summary.

    A module counts as *completed* once every question has been answered
    correctly at least once (tracked by the caller across sessions). Here we
    treat the supplied ``graded`` list as the definitive set of best attempts.
    """
    answered = len(graded)
    correct = sum(1 for g in graded if g.correct)
    xp = sum(g.points_awarded for g in graded)
    completed = correct == len(module.questions) and len(module.questions) > 0
    return ModuleScore(
        module_id=module.id,
        answered=answered,
        correct=correct,
        xp=xp,
        total_questions=len(module.questions),
        completed=completed,
    )


def level_for_xp(total_xp: int) -> int:
    """Map cumulative XP to a level. Each level costs 100 XP more than the last
    (level 1: 0–99, level 2: 100–299, level 3: 300–599, ...)."""
    level = 1
    threshold = 100
    step = 100
    xp = total_xp
    while xp >= threshold:
        xp -= threshold
        level += 1
        threshold += step
    return level


def xp_to_next_level(total_xp: int) -> int:
    """XP still required to reach the next level."""
    level = 1
    threshold = 100
    step = 100
    xp = total_xp
    while xp >= threshold:
        xp -= threshold
        level += 1
        threshold += step
    return threshold - xp


def evaluate_badges(
    store: ContentStore,
    completed_module_ids: set[str],
    total_xp: int,
    already_earned: set[str],
) -> list[Badge]:
    """Return badges newly earned given current state (excludes already-earned).

    Supports three criteria types:
      * ``module_complete`` — the given module id is complete
      * ``track_complete``  — every module in the named track is complete
      * ``xp_threshold``    — cumulative XP meets/exceeds the value
    """
    newly: list[Badge] = []
    for badge in store.badges:
        if badge.id in already_earned:
            continue
        if _badge_satisfied(badge, store, completed_module_ids, total_xp):
            newly.append(badge)
    return newly


def _badge_satisfied(
    badge: Badge,
    store: ContentStore,
    completed_module_ids: set[str],
    total_xp: int,
) -> bool:
    if badge.criteria_type == "module_complete":
        return badge.criteria_value in completed_module_ids
    if badge.criteria_type == "track_complete":
        track_modules = store.modules_in_track(badge.criteria_value)
        return bool(track_modules) and all(
            m.id in completed_module_ids for m in track_modules
        )
    if badge.criteria_type == "xp_threshold":
        try:
            return total_xp >= int(badge.criteria_value)
        except ValueError:
            return False
    return False
