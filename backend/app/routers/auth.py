"""Auth router — lightweight username sessions.

No password today (partner-enablement, low-stakes). The endpoint is the single
place a real IdP would plug in: swap the body for an OIDC code exchange and
issue a JWT instead of returning the username as the token.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..deps import get_current_user
from ..metrics import logins_total
from ..models import User
from ..schemas import LoginRequest, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=UserOut)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> UserOut:
    """Log in or auto-register a learner by username."""
    result = await session.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            username=body.username,
            display_name=body.display_name or body.username.replace("-", " ").title(),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    logins_total.inc()
    # The token IS the username today; kept opaque in the contract for the future.
    return UserOut(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        token=user.username,
    )


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> UserOut:
    """Return the current session's user."""
    return UserOut(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        token=user.username,
    )
