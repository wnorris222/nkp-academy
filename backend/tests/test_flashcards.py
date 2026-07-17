"""Tests for flashcard deck building and the flashcards API.

Cards are authored content rather than a projection of the quiz, so these
guard the loader (every card is usable and well-formed), the deck selection,
and the promise that flashcards stay out of the scoring path.
"""
from __future__ import annotations

import pytest

from app import flashcards as fc

VALID_KINDS = {"term", "concept", "command", "fact"}


# ---- Pure deck logic ----

def test_content_ships_flashcard_decks(content_store):
    assert content_store.flashcard_decks, "expected authored decks under content/flashcards"


def test_all_deck_is_every_card_from_every_deck(content_store):
    cards = fc.build_deck(content_store)
    total = sum(len(d.cards) for d in content_store.flashcard_decks)
    assert len(cards) == total


def test_every_card_has_a_front_and_a_back(content_store):
    for card in fc.build_deck(content_store):
        assert card.front.strip(), f"{card.id} has an empty front"
        assert card.back.strip(), f"{card.id} has an empty back"


def test_every_card_has_a_known_kind(content_store):
    for card in fc.build_deck(content_store):
        assert card.kind in VALID_KINDS, f"{card.id} has kind={card.kind!r}"


def test_card_ids_are_unique_across_decks(content_store):
    ids = [c.id for c in fc.build_deck(content_store)]
    assert len(ids) == len(set(ids)), "duplicate flashcard ids"


def test_cards_are_not_copies_of_quiz_questions(content_store):
    """The whole point of the redesign: cards teach, they don't restate the quiz."""
    prompts = {q.prompt.strip() for m in content_store.modules for q in m.questions}
    clashes = [c.id for c in fc.build_deck(content_store) if c.front.strip() in prompts]
    assert not clashes, f"cards duplicate quiz prompts: {clashes}"


def test_page_reference_is_rendered_for_display(content_store):
    """`page: 18` in YAML becomes a human-readable ref, not a bare number."""
    refs = [c.ref for c in fc.build_deck(content_store) if c.ref]
    assert refs, "expected at least one card with a doc reference"
    assert all(r.startswith("NKP 2.17 Guide · p.") for r in refs)


def test_named_deck_only_contains_its_own_cards(content_store):
    deck = content_store.flashcard_decks[0]
    cards = fc.build_deck(content_store, deck.id)
    assert [c.id for c in cards] == [c.id for c in deck.cards]


def test_unknown_deck_builds_empty(content_store):
    assert fc.build_deck(content_store, "does-not-exist") == []


def test_deck_title(content_store):
    deck = content_store.flashcard_decks[0]
    assert fc.deck_title(content_store, fc.DECK_ALL) == "All cards"
    assert fc.deck_title(content_store, deck.id) == deck.title


def test_list_decks_covers_every_deck_plus_all(content_store):
    decks = fc.list_decks(content_store)
    assert len(decks) == len(content_store.flashcard_decks) + 1
    all_deck = next(d for d in decks if d.id == fc.DECK_ALL)
    assert all_deck.count == sum(len(d.cards) for d in content_store.flashcard_decks)


# ---- API ----

@pytest.mark.asyncio
async def test_list_decks_endpoint(client):
    resp = await client.get("/api/flashcards/decks")
    assert resp.status_code == 200
    decks = resp.json()
    assert any(d["id"] == "all" for d in decks)
    assert all(d["count"] > 0 for d in decks)
    assert all(d["title"] and d["icon"] for d in decks)


@pytest.mark.asyncio
async def test_get_all_deck(client):
    resp = await client.get("/api/flashcards")
    assert resp.status_code == 200
    body = resp.json()
    assert body["deck_id"] == "all"
    assert body["count"] == len(body["cards"])
    card = body["cards"][0]
    assert card["front"] and card["back"] and card["kind"] in VALID_KINDS


@pytest.mark.asyncio
async def test_get_named_deck(client):
    resp = await client.get("/api/flashcards", params={"deck_id": "fc-fundamentals"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] > 0
    assert body["title"] == "NKP Fundamentals"


@pytest.mark.asyncio
async def test_command_cards_carry_code(client):
    resp = await client.get("/api/flashcards", params={"deck_id": "fc-cli"})
    assert resp.status_code == 200
    cards = resp.json()["cards"]
    assert any(c["code"] for c in cards), "expected the CLI deck to ship code snippets"


@pytest.mark.asyncio
async def test_unknown_deck_404s(client):
    resp = await client.get("/api/flashcards", params={"deck_id": "does-not-exist"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_flashcards_require_no_auth(client):
    """Decks are public self-study: no session token needed."""
    resp = await client.get("/api/flashcards", params={"deck_id": "all"})
    assert resp.status_code == 200
