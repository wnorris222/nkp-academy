"""Quiz router — submit an answer and receive instant, graded feedback."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from .. import scoring, services
from ..content import ContentStore
from ..database import get_session
from ..deps import get_current_user, get_store
from ..models import User
from ..schemas import AnswerSubmission, BadgeOut, GradeOut, SourceOut

router = APIRouter(prefix="/api/quiz", tags=["quiz"])


@router.post("/{module_id}/answer", response_model=GradeOut)
async def submit_answer(
    module_id: str,
    body: AnswerSubmission,
    store: ContentStore = Depends(get_store),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> GradeOut:
    """Grade a single answer, persist it, update XP/progress, and award badges."""
    question = store.question(module_id, body.question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found in module")

    graded, new_badges = await services.record_answer(
        session, store, user, module_id, question, body.selected
    )
    total_xp = await services.get_total_xp(session, user.id)

    return GradeOut(
        question_id=graded.question_id,
        correct=graded.correct,
        points_awarded=graded.points_awarded,
        correct_options=list(graded.correct_options),
        explanation=graded.explanation,
        source=SourceOut(**vars(question.source)) if question.source else None,
        total_xp=total_xp,
        level=scoring.level_for_xp(total_xp),
        xp_to_next_level=scoring.xp_to_next_level(total_xp),
        new_badges=[
            BadgeOut(id=b.id, name=b.name, description=b.description, icon=b.icon)
            for b in new_badges
        ],
    )
