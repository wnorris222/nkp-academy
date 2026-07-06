"""Practice-exam router — generate a section-spanning mock exam and grade it.

Stateless by design: no auth or DB writes, mirroring the read-only content
endpoints. Generating returns questions without answers; submitting grades the
batch and returns a score report with a per-section breakdown and answer review.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import exam
from ..config import get_settings
from ..content import ContentStore
from ..deps import get_store
from ..metrics import exams_submitted_total
from ..schemas import (
    ExamOut,
    ExamQuestionOut,
    ExamQuestionResultOut,
    ExamReportOut,
    ExamSectionResultOut,
    ExamSubmitRequest,
    OptionOut,
    SourceOut,
)

router = APIRouter(prefix="/api/exam", tags=["exam"])
settings = get_settings()


@router.get("", response_model=ExamOut)
async def generate_exam(
    count: int = Query(default=None, ge=5, le=200),
    tracks: str | None = Query(
        default=None, description="Comma-separated track names to draw from"
    ),
    store: ContentStore = Depends(get_store),
) -> ExamOut:
    """Generate a randomized, section-balanced practice exam (answers withheld)."""
    n = count or settings.exam_default_count
    track_filter = [t.strip() for t in tracks.split(",") if t.strip()] if tracks else None

    items = exam.build_exam(store, n, track_filter)
    if not items:
        raise HTTPException(status_code=404, detail="No questions available for exam")

    questions = [
        ExamQuestionOut(
            module_id=it.module_id,
            module_title=it.module_title,
            track=it.track,
            question_id=it.question.id,
            type=it.question.type,
            prompt=it.question.prompt,
            options=[OptionOut(id=o.id, text=o.text) for o in it.question.options],
            points=it.question.points,
            difficulty=it.question.difficulty,
            multiple=len(it.question.correct_set) > 1,
        )
        for it in items
    ]
    return ExamOut(
        count=len(questions),
        pass_threshold=settings.exam_pass_threshold,
        questions=questions,
    )


@router.post("/submit", response_model=ExamReportOut)
async def submit_exam(
    body: ExamSubmitRequest,
    store: ContentStore = Depends(get_store),
) -> ExamReportOut:
    """Grade a completed exam and return a scored report."""
    submissions = [(a.module_id, a.question_id, a.selected) for a in body.answers]
    report = exam.grade_exam(store, submissions, settings.exam_pass_threshold)

    exams_submitted_total.labels(result="pass" if report.passed else "fail").inc()

    return ExamReportOut(
        total=report.total,
        answered=report.answered,
        correct=report.correct,
        score_pct=report.score_pct,
        passed=report.passed,
        pass_threshold=report.pass_threshold,
        sections=[
            ExamSectionResultOut(track=s.track, correct=s.correct, total=s.total)
            for s in report.sections
        ],
        results=[
            ExamQuestionResultOut(
                module_id=r.module_id,
                question_id=r.question_id,
                track=r.track,
                correct=r.correct,
                correct_options=list(r.correct_options),
                explanation=r.explanation,
                source=SourceOut(**vars(r.source)) if r.source else None,
            )
            for r in report.results
        ],
    )
