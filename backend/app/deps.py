"""Shared FastAPI dependencies.

The content store is loaded once at startup and stashed on ``app.state``; auth
is funnelled through a single :func:`get_current_user` seam so a future
OIDC/SSO provider can replace the username-token scheme without touching routers.
"""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .content import ContentStore
from .database import get_session
from .models import User


def get_store(request: Request) -> ContentStore:
    """Return the process-wide content store loaded at startup."""
    store: ContentStore | None = getattr(request.app.state, "content_store", None)
    if store is None:  # pragma: no cover - would indicate a startup bug
        raise HTTPException(status_code=500, detail="Content store not initialised")
    return store


async def get_current_user(
    session: AsyncSession = Depends(get_session),
    authorization: str | None = Header(default=None),
    x_session_token: str | None = Header(default=None, alias="X-Session-Token"),
) -> User:
    """Resolve the authenticated user from a session token.

    Today the token is simply the username (accepted via ``X-Session-Token`` or
    an ``Authorization: Bearer <token>`` header). To add OIDC later, validate a
    JWT here and look the user up by ``oidc_subject`` — the rest of the app is
    unaffected.
    """
    token = x_session_token
    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing session token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await session.execute(select(User).where(User.username == token))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )
    return user
