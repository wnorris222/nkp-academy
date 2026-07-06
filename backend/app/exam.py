"""Practice-exam logic: sample questions across sections, then grade a batch.

A practice exam is a *stateless* mock test — it never touches the database or a
user's module progress/XP. Questions are sampled across tracks (sections) so a
single exam exercises the whole syllabus, and grading is a pure function of the
content store (which holds the correct answers), so no exam state needs to be
persisted between generate and submit.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from . import scoring
from .content import ContentStore, Question, Source


@dataclass(frozen=True)
class ExamItem:
    """One sampled question plus the module/track it came from."""

    track: str
    module_id: str
    module_title: str
    question: Question


def build_exam(
    store: ContentStore,
    count: int,
    tracks: list[str] | None = None,
    rng: random.Random | None = None,
) -> list[ExamItem]:
    """Sample ``count`` questions spread across the eligible tracks.

    Allocation is proportional to each track's question pool (largest-remainder
    method) so every section is represented roughly in line with its size, then
    questions are sampled without replacement within each track and the final
    list is shuffled. ``tracks`` optionally restricts which sections are drawn
    from. Returns fewer items only if the pool is smaller than ``count``.
    """
    rng = rng or random.Random()

    modules = [m for m in store.modules if tracks is None or m.track in tracks]
    pool = [(m, q) for m in modules for q in m.questions]
    if not pool:
        return []
    count = min(count, len(pool))

    by_track: dict[str, list] = {}
    for m in modules:
        by_track.setdefault(m.track, []).append(m)

    track_question_counts = {
        t: sum(len(m.questions) for m in ms) for t, ms in by_track.items()
    }
    total_q = sum(track_question_counts.values())

    # Largest-remainder proportional allocation across tracks.
    alloc: dict[str, int] = {}
    remainders: list[tuple[float, str]] = []
    assigned = 0
    for t, qc in track_question_counts.items():
        exact = count * qc / total_q
        base = int(exact)
        alloc[t] = base
        assigned += base
        remainders.append((exact - base, t))
    remainders.sort(reverse=True)
    for i in range(count - assigned):
        alloc[remainders[i % len(remainders)][1]] += 1

    items: list[ExamItem] = []
    for t, ms in by_track.items():
        track_pool = [(m, q) for m in ms for q in m.questions]
        k = min(alloc[t], len(track_pool))
        for m, q in rng.sample(track_pool, k):
            items.append(
                ExamItem(track=t, module_id=m.id, module_title=m.title, question=q)
            )
    rng.shuffle(items)
    return items


@dataclass(frozen=True)
class QuestionResult:
    module_id: str
    question_id: str
    track: str
    correct: bool
    correct_options: tuple[str, ...]
    explanation: str
    source: Source | None = None


@dataclass(frozen=True)
class SectionResult:
    track: str
    correct: int
    total: int


@dataclass(frozen=True)
class ExamReport:
    total: int
    answered: int
    correct: int
    score_pct: float
    passed: bool
    pass_threshold: float
    sections: list[SectionResult]
    results: list[QuestionResult]


def grade_exam(
    store: ContentStore,
    submissions: list[tuple[str, str, list[str]]],
    pass_threshold: float,
) -> ExamReport:
    """Grade a batch of ``(module_id, question_id, selected)`` submissions.

    Unknown module/question references are skipped. An unanswered question
    (empty ``selected``) grades as incorrect but still counts toward the total,
    so the client should submit every exam question. Score is the fraction of
    correct answers; ``passed`` is score >= ``pass_threshold``.
    """
    results: list[QuestionResult] = []
    section_totals: dict[str, list[int]] = {}  # track -> [correct, total]

    for module_id, question_id, selected in submissions:
        module = store.module(module_id)
        question: Question | None = store.question(module_id, question_id)
        if module is None or question is None:
            continue
        graded = scoring.grade_answer(question, selected)
        results.append(
            QuestionResult(
                module_id=module_id,
                question_id=question_id,
                track=module.track,
                correct=graded.correct,
                correct_options=graded.correct_options,
                explanation=graded.explanation,
                source=question.source,
            )
        )
        bucket = section_totals.setdefault(module.track, [0, 0])
        bucket[1] += 1
        if graded.correct:
            bucket[0] += 1

    total = len(results)
    correct = sum(1 for r in results if r.correct)
    score_pct = (correct / total) if total else 0.0

    sections = [
        SectionResult(track=t, correct=c, total=n)
        for t, (c, n) in sorted(section_totals.items())
    ]

    return ExamReport(
        total=total,
        answered=sum(1 for _, _, sel in submissions if sel),
        correct=correct,
        score_pct=score_pct,
        passed=score_pct >= pass_threshold,
        pass_threshold=pass_threshold,
        sections=sections,
        results=results,
    )
