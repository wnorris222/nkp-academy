"""Flashcard decks, derived from the existing quiz content.

A flashcard is a *projection* of a question rather than a new content type:
front is the prompt, back is the answer plus its explanation and citation.
Deriving them means ~300 cards exist for free and stay in lockstep with the
quiz — fix a question or a doc link once and both modes get the fix.

Self-graded and stateless by design. The learner decides whether they knew the
answer, so nothing is persisted and no XP is awarded: a tick you give yourself
would be trivially farmable and would corrupt the leaderboard. Grading that
counts lives in the quiz (:mod:`app.scoring`).
"""
from __future__ import annotations

from dataclasses import dataclass

from .content import ContentStore, Module, Question, Source

# Deck id prefixes used in the API contract, e.g. "module:ncpcn-s1-bastion".
DECK_ALL = "all"
_MODULE_PREFIX = "module:"
_TRACK_PREFIX = "track:"


@dataclass(frozen=True)
class Flashcard:
    """One card: prompt on the front, answer/explanation/source on the back."""

    id: str
    module_id: str
    module_title: str
    track: str
    front: str
    answer: str  # short: the correct option text(s)
    back: str  # long: the explanation
    source: Source | None


@dataclass(frozen=True)
class DeckInfo:
    """A selectable deck (all cards, one track, or one module)."""

    id: str
    title: str
    kind: str  # "all" | "track" | "module"
    count: int


def answer_text(question: Question) -> str:
    """Render a question's correct answer as human-readable text.

    Uses the option text rather than the raw ids so the back of the card reads
    like prose ("False", "8 vCPU, 16 GB memory, 80 GB disk"). Multi-select
    answers are joined, in id order, so the output is deterministic.
    """
    by_id = {o.id: o.text for o in question.options}
    picks = [by_id.get(cid, cid) for cid in sorted(question.correct_set)]
    return " · ".join(picks)


def build_card(module: Module, question: Question) -> Flashcard:
    return Flashcard(
        id=question.id,
        module_id=module.id,
        module_title=module.title,
        track=module.track,
        front=question.prompt,
        answer=answer_text(question),
        back=question.explanation,
        source=question.source,
    )


def build_deck(
    store: ContentStore,
    module_id: str | None = None,
    track: str | None = None,
) -> list[Flashcard]:
    """Return cards for one module, one track, or the whole syllabus.

    Order follows module order then question order, so a learner can work
    through a deck systematically; the client shuffles when asked.
    """
    modules = list(store.modules)
    if module_id is not None:
        modules = [m for m in modules if m.id == module_id]
    elif track is not None:
        modules = [m for m in modules if m.track == track]
    return [build_card(m, q) for m in modules for q in m.questions]


def parse_deck_id(deck_id: str) -> tuple[str | None, str | None]:
    """Map a deck id to ``(module_id, track)`` filters.

    ``"all"`` -> (None, None); ``"module:<id>"`` and ``"track:<name>"`` select
    one of each. Unknown shapes fall back to the full deck.
    """
    if deck_id.startswith(_MODULE_PREFIX):
        return deck_id[len(_MODULE_PREFIX) :], None
    if deck_id.startswith(_TRACK_PREFIX):
        return None, deck_id[len(_TRACK_PREFIX) :]
    return None, None


def deck_title(store: ContentStore, deck_id: str) -> str:
    module_id, track = parse_deck_id(deck_id)
    if module_id:
        module = store.module(module_id)
        return module.title if module else module_id
    if track:
        return track
    return "All cards"


def list_decks(store: ContentStore) -> list[DeckInfo]:
    """All selectable decks: everything, then per track, then per module."""
    decks = [
        DeckInfo(
            id=DECK_ALL,
            title="All cards",
            kind="all",
            count=sum(len(m.questions) for m in store.modules),
        )
    ]
    for track in store.tracks():
        modules = store.modules_in_track(track)
        decks.append(
            DeckInfo(
                id=f"{_TRACK_PREFIX}{track}",
                title=track,
                kind="track",
                count=sum(len(m.questions) for m in modules),
            )
        )
    for module in store.modules:
        decks.append(
            DeckInfo(
                id=f"{_MODULE_PREFIX}{module.id}",
                title=module.title,
                kind="module",
                count=len(module.questions),
            )
        )
    return decks
