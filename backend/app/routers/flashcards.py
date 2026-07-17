"""Flashcards router — purpose-written self-study decks.

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
from ..schemas import DeckOut, FlashcardDeckOut, FlashcardOut

router = APIRouter(prefix="/api/flashcards", tags=["flashcards"])


@router.get("/decks", response_model=list[DeckOut])
async def list_decks(store: ContentStore = Depends(get_store)) -> list[DeckOut]:
    """List the selectable decks, in authored order, then the everything deck."""
    return [
        DeckOut(id=d.id, title=d.title, icon=d.icon, summary=d.summary, count=d.count)
        for d in fc.list_decks(store)
    ]


@router.get("", response_model=FlashcardDeckOut)
async def get_deck(
    deck_id: str = Query(default=fc.DECK_ALL, description="all | <deck id>"),
    store: ContentStore = Depends(get_store),
) -> FlashcardDeckOut:
    """Return every card in a deck.

    Cards come back in authored order; shuffling is the client's job so a
    learner can also work through a deck systematically.
    """
    if deck_id != fc.DECK_ALL and store.flashcard_deck(deck_id) is None:
        raise HTTPException(status_code=404, detail="Deck not found")

    cards = fc.build_deck(store, deck_id)
    flashcard_decks_served_total.labels(kind=deck_id).inc()

    return FlashcardDeckOut(
        deck_id=deck_id,
        title=fc.deck_title(store, deck_id),
        count=len(cards),
        cards=[FlashcardOut(**vars(c)) for c in cards],
    )
