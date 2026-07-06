"""Content router — exposes modules, questions, tracks, and badge catalog.

Correct answers and explanations are never returned here; grading happens in the
quiz router after submission so answers can't be scraped from the API.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..content import ContentStore, Module
from ..deps import get_store
from ..schemas import (
    BadgeOut,
    ModuleDetailOut,
    ModuleSummaryOut,
    OptionOut,
    QuestionOut,
)

router = APIRouter(prefix="/api/content", tags=["content"])


def _summary(module: Module) -> ModuleSummaryOut:
    return ModuleSummaryOut(
        id=module.id,
        title=module.title,
        track=module.track,
        order=module.order,
        summary=module.summary,
        icon=module.icon,
        question_count=len(module.questions),
        total_points=module.total_points,
    )


@router.get("/modules", response_model=list[ModuleSummaryOut])
async def list_modules(store: ContentStore = Depends(get_store)) -> list[ModuleSummaryOut]:
    """List all modules (ordered), without questions."""
    return [_summary(m) for m in store.modules]


@router.get("/tracks", response_model=list[str])
async def list_tracks(store: ContentStore = Depends(get_store)) -> list[str]:
    """List track names in display order."""
    return store.tracks()


@router.get("/modules/{module_id}", response_model=ModuleDetailOut)
async def get_module(
    module_id: str,
    store: ContentStore = Depends(get_store),
) -> ModuleDetailOut:
    """Fetch one module with its questions (answers withheld)."""
    module = store.module(module_id)
    if module is None:
        raise HTTPException(status_code=404, detail="Module not found")

    questions = [
        QuestionOut(
            id=q.id,
            type=q.type,
            prompt=q.prompt,
            options=[OptionOut(id=o.id, text=o.text) for o in q.options],
            points=q.points,
            difficulty=q.difficulty,
        )
        for q in module.questions
    ]
    base = _summary(module)
    return ModuleDetailOut(**base.model_dump(), questions=questions)


@router.get("/badges", response_model=list[BadgeOut])
async def list_badges(store: ContentStore = Depends(get_store)) -> list[BadgeOut]:
    """Return the full badge catalog."""
    return [
        BadgeOut(id=b.id, name=b.name, description=b.description, icon=b.icon)
        for b in store.badges
    ]
