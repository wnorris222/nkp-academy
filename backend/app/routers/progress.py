"""Progress router — a learner's XP, level, per-module progress, and badges."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import scoring, services
from ..content import ContentStore
from ..database import get_session
from ..deps import get_current_user, get_store
from ..models import ModuleProgress, User
from ..schemas import (
    BadgeOut,
    ModuleProgressOut,
    ProgressOut,
)

router = APIRouter(prefix="/api/progress", tags=["progress"])


@router.get("", response_model=ProgressOut)
async def my_progress(
    store: ContentStore = Depends(get_store),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ProgressOut:
    """Return the current user's full progress snapshot."""
    progress_rows = (
        await session.execute(
            select(ModuleProgress).where(ModuleProgress.user_id == user.id)
        )
    ).scalars().all()

    earned_ids = await services.get_earned_badge_ids(session, user.id)
    badges = [
        BadgeOut(id=b.id, name=b.name, description=b.description, icon=b.icon)
        for b in store.badges
        if b.id in earned_ids
    ]

    total_xp = await services.get_total_xp(session, user.id)

    return ProgressOut(
        username=user.username,
        display_name=user.display_name,
        total_xp=total_xp,
        level=scoring.level_for_xp(total_xp),
        xp_to_next_level=scoring.xp_to_next_level(total_xp),
        modules=[
            ModuleProgressOut(
                module_id=p.module_id,
                questions_answered=p.questions_answered,
                questions_correct=p.questions_correct,
                xp_earned=p.xp_earned,
                completed=p.completed,
            )
            for p in progress_rows
        ],
        badges=badges,
    )
