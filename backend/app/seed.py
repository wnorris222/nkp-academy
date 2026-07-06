"""Demo data seeding.

Creates a few sample learners with realistic progress so the leaderboard and
dashboard look alive on first run. Idempotent: skips if the demo users already
exist. Real content comes from YAML, never from here.
"""
from __future__ import annotations

from sqlalchemy import select

from .content import ContentStore
from .database import SessionLocal
from .models import User
from .services import record_answer

# (username, display_name, correct-answer ratio) — how much of the content each
# demo user has completed correctly.
_DEMO_USERS = [
    ("priya-partner", "Priya (Acme Cloud)", 1.0),
    ("diego-se", "Diego (NextGen SI)", 0.75),
    ("mei-architect", "Mei (Summit Partners)", 0.5),
]


async def seed_demo_data(store: ContentStore) -> None:
    """Populate demo learners and their answers if not already present."""
    async with SessionLocal() as session:
        existing = (
            await session.execute(
                select(User.username).where(
                    User.username.in_([u[0] for u in _DEMO_USERS])
                )
            )
        ).scalars().all()
        if existing:
            return  # already seeded

        for username, display_name, ratio in _DEMO_USERS:
            user = User(username=username, display_name=display_name)
            session.add(user)
            await session.commit()
            await session.refresh(user)

            for module in store.modules:
                cutoff = int(len(module.questions) * ratio)
                for idx, question in enumerate(module.questions):
                    # Answer correctly up to the cutoff, then stop for that module.
                    if idx >= cutoff:
                        break
                    selected = list(question.correct)
                    await record_answer(
                        session, store, user, module.id, question, selected
                    )
