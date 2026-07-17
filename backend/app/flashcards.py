"""Flashcard decks — purpose-written study content.

Cards are authored in ``content/flashcards/*.yaml``, not derived from the quiz.
The two modes teach differently: a quiz question tests whether you can pick the
right option under exam conditions, while a card teaches one thing — a term, a
concept, a command, or a fact — and is read front-to-back. Projecting questions
into cards produced distractor-shaped prompts and answers that only made sense
if you had already seen the options, so the decks are written for recall.

Self-graded and stateless by design. The learner decides whether they knew the
answer, so nothing is persisted and no XP is awarded: a tick you give yourself
would be trivially farmable and would corrupt the leaderboard. Grading that
counts lives in the quiz (:mod:`app.scoring`).
"""
from __future__ import annotations

from dataclasses import dataclass

from .content import ContentStore, Flashcard

DECK_ALL = "all"


@dataclass(frozen=True)
class DeckInfo:
    """A selectable deck, for the picker screen."""

    id: str
    title: str
    icon: str
    summary: str
    count: int


def build_deck(store: ContentStore, deck_id: str = DECK_ALL) -> list[Flashcard]:
    """Return the cards in a deck, or every card for :data:`DECK_ALL`.

    Order follows the authored deck order so a learner can work through the
    material systematically; the client shuffles when asked.
    """
    if deck_id == DECK_ALL:
        return [c for d in store.flashcard_decks for c in d.cards]
    deck = store.flashcard_deck(deck_id)
    return list(deck.cards) if deck else []


def deck_title(store: ContentStore, deck_id: str) -> str:
    if deck_id == DECK_ALL:
        return "All cards"
    deck = store.flashcard_deck(deck_id)
    return deck.title if deck else deck_id


def list_decks(store: ContentStore) -> list[DeckInfo]:
    """Every selectable deck: the authored decks, then an everything deck."""
    decks = [
        DeckInfo(id=d.id, title=d.title, icon=d.icon, summary=d.summary, count=len(d.cards))
        for d in store.flashcard_decks
    ]
    decks.append(
        DeckInfo(
            id=DECK_ALL,
            title="All cards",
            icon="star",
            summary="Every card from every deck, in syllabus order.",
            count=sum(d.count for d in decks),
        )
    )
    return decks
