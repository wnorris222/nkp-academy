"""Flashcards router — self-study decks derived from the quiz content.

Read-only and stateless: no auth, no persistence, no XP. See
:mod:`app.flashcards` for why self-graded review is deliberately kept out of
the scoring/leaderboard path.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import flashcards as fc
from ..content import ContentStore
from ..deps import get_store
from ..metrics import flashcard_decks_served_total
from ..schemas import DeckOut, FlashcardDeckOut, FlashcardOut, SourceOut

router = APIRouter(prefix="/api/flashcards", tags=["flashcards"])


@router.get("/decks", response_model=list[DeckOut])
async def list_decks(store: ContentStore = Depends(get_store)) -> list[DeckOut]:
    """List selectable decks: all cards, then one per track, then per module."""
    return [
        DeckOut(id=d.id, title=d.title, kind=d.kind, count=d.count)
        for d in fc.list_decks(store)
    ]


@router.get("", response_model=FlashcardDeckOut)
async def get_deck(
    deck_id: str = Query(default=fc.DECK_ALL, description="all | track:<name> | module:<id>"),
    store: ContentStore = Depends(get_store),
) -> FlashcardDeckOut:
    """Return every card in a deck.

    Cards come back in syllabus order; shuffling is the client's job so a
    learner can also work through a deck systematically.
    """
    module_id, track = fc.parse_deck_id(deck_id)

    if module_id is not None and store.module(module_id) is None:
        raise HTTPException(status_code=404, detail="Module not found")
    if track is not None and track not in store.tracks():
        raise HTTPException(status_code=404, detail="Track not found")

    cards = fc.build_deck(store, module_id=module_id, track=track)
    kind = "module" if module_id else "track" if track else "all"
    flashcard_decks_served_total.labels(kind=kind).inc()

    return FlashcardDeckOut(
        deck_id=deck_id,
        title=fc.deck_title(store, deck_id),
        count=len(cards),
        cards=[
            FlashcardOut(
                id=c.id,
                module_id=c.module_id,
                module_title=c.module_title,
                track=c.track,
                front=c.front,
                answer=c.answer,
                back=c.back,
                source=SourceOut(**vars(c.source)) if c.source else None,
            )
            for c in cards
        ],
    )
