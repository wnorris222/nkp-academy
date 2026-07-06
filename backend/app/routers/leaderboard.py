"""Leaderboard router — ranks learners by total XP."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import scoring
from ..database import get_session
from ..models import ModuleProgress, User, UserBadge
from ..schemas import LeaderboardEntry, LeaderboardOut

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])


@router.get("", response_model=LeaderboardOut)
async def leaderboard(
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> LeaderboardOut:
    """Top learners by total XP, with level and badge count."""
    xp_col = func.coalesce(func.sum(ModuleProgress.xp_earned), 0).label("total_xp")
    badge_sub = (
        select(UserBadge.user_id, func.count().label("badge_count"))
        .group_by(UserBadge.user_id)
        .subquery()
    )

    stmt = (
        select(
            User.username,
            User.display_name,
            xp_col,
            func.coalesce(badge_sub.c.badge_count, 0).label("badge_count"),
        )
        .join(ModuleProgress, ModuleProgress.user_id == User.id, isouter=True)
        .join(badge_sub, badge_sub.c.user_id == User.id, isouter=True)
        .group_by(User.id, badge_sub.c.badge_count)
        .order_by(xp_col.desc(), User.username.asc())
        .limit(limit)
    )

    rows = (await session.execute(stmt)).all()
    entries = [
        LeaderboardEntry(
            rank=i + 1,
            username=r.username,
            display_name=r.display_name,
            total_xp=int(r.total_xp or 0),
            level=scoring.level_for_xp(int(r.total_xp or 0)),
            badge_count=int(r.badge_count or 0),
        )
        for i, r in enumerate(rows)
    ]
    return LeaderboardOut(entries=entries, generated_at=datetime.now(UTC))
