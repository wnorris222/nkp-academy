"""Service layer: orchestrates scoring, persistence, and badge awards.

Routers stay thin by delegating stateful workflows here. Everything in this
module is async and session-scoped; the pure math lives in :mod:`app.scoring`.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from . import scoring
from .content import Badge, ContentStore, Question
from .metrics import badges_awarded_total, quiz_answers_total
from .models import Attempt, ModuleProgress, User, UserBadge


async def record_answer(
    session: AsyncSession,
    store: ContentStore,
    user: User,
    module_id: str,
    question: Question,
    selected: list[str],
) -> tuple[scoring.GradedAnswer, list[Badge]]:
    """Grade an answer, persist it, refresh module progress, and award badges.

    Returns the graded answer and any newly-earned badges. Progress only ever
    improves: a question already answered correctly stays correct even if a
    later attempt is wrong (best-attempt semantics).
    """
    graded = scoring.grade_answer(question, selected)
    quiz_answers_total.labels(result="correct" if graded.correct else "incorrect").inc()

    session.add(
        Attempt(
            user_id=user.id,
            module_id=module_id,
            question_id=question.id,
            selected=",".join(selected),
            correct=graded.correct,
            points_awarded=graded.points_awarded,
        )
    )
    await session.flush()

    await _refresh_module_progress(session, store, user, module_id)
    total_xp = await get_total_xp(session, user.id)
    new_badges = await _award_badges(session, store, user, total_xp)

    await session.commit()
    return graded, new_badges


async def _refresh_module_progress(
    session: AsyncSession,
    store: ContentStore,
    user: User,
    module_id: str,
) -> None:
    """Recompute a user's best-attempt progress for one module from attempts."""
    module = store.module(module_id)
    if module is None:
        return

    # Best attempt per question: correct if ever answered correctly.
    rows = (
        await session.execute(
            select(
                Attempt.question_id,
                func.max(Attempt.correct.cast(_INT)).label("ever_correct"),
                func.max(Attempt.points_awarded).label("best_points"),
            )
            .where(Attempt.user_id == user.id, Attempt.module_id == module_id)
            .group_by(Attempt.question_id)
        )
    ).all()

    answered = len(rows)
    correct = sum(1 for r in rows if r.ever_correct)
    xp = sum(r.best_points or 0 for r in rows)
    completed = correct == len(module.questions) and len(module.questions) > 0

    existing = (
        await session.execute(
            select(ModuleProgress).where(
                ModuleProgress.user_id == user.id,
                ModuleProgress.module_id == module_id,
            )
        )
    ).scalar_one_or_none()

    if existing is None:
        session.add(
            ModuleProgress(
                user_id=user.id,
                module_id=module_id,
                questions_answered=answered,
                questions_correct=correct,
                xp_earned=xp,
                completed=completed,
            )
        )
    else:
        existing.questions_answered = answered
        existing.questions_correct = correct
        existing.xp_earned = xp
        existing.completed = completed
    await session.flush()


async def _award_badges(
    session: AsyncSession,
    store: ContentStore,
    user: User,
    total_xp: int,
) -> list[Badge]:
    """Persist any newly-earned badges and return them."""
    completed = await get_completed_module_ids(session, user.id)
    earned = await get_earned_badge_ids(session, user.id)

    newly = scoring.evaluate_badges(store, completed, total_xp, earned)
    for badge in newly:
        session.add(UserBadge(user_id=user.id, badge_id=badge.id))
        badges_awarded_total.labels(badge_id=badge.id).inc()
    if newly:
        await session.flush()
    return newly


# ---- Read helpers ----

async def get_total_xp(session: AsyncSession, user_id: int) -> int:
    """Sum of best-attempt XP across all modules for a user."""
    total = (
        await session.execute(
            select(func.coalesce(func.sum(ModuleProgress.xp_earned), 0)).where(
                ModuleProgress.user_id == user_id
            )
        )
    ).scalar_one()
    return int(total or 0)


async def get_completed_module_ids(session: AsyncSession, user_id: int) -> set[str]:
    rows = (
        await session.execute(
            select(ModuleProgress.module_id).where(
                ModuleProgress.user_id == user_id,
                ModuleProgress.completed.is_(True),
            )
        )
    ).scalars()
    return set(rows)


async def get_earned_badge_ids(session: AsyncSession, user_id: int) -> set[str]:
    rows = (
        await session.execute(
            select(UserBadge.badge_id).where(UserBadge.user_id == user_id)
        )
    ).scalars()
    return set(rows)


# SQLAlchemy needs an explicit type for the boolean->int cast used above.
from sqlalchemy import Integer as _INT  # noqa: E402
