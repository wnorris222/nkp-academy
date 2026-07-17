"""Tests for flashcard deck building and the flashcards API.

Cards are a projection of the quiz content, so these guard the projection
(every card has a usable front/back) and the deck filters.
"""
from __future__ import annotations

import pytest

from app import flashcards as fc


# ---- Pure deck logic ----

def test_all_deck_has_one_card_per_question(content_store):
    cards = fc.build_deck(content_store)
    total = sum(len(m.questions) for m in content_store.modules)
    assert len(cards) == total


def test_every_card_has_a_front_and_a_back(content_store):
    for card in fc.build_deck(content_store):
        assert card.front.strip(), f"{card.id} has an empty front"
        assert card.back.strip(), f"{card.id} has an empty back"
        assert card.answer.strip(), f"{card.id} has an empty answer"


def test_answer_text_renders_option_text_not_ids(content_store):
    module = content_store.module("ncpcn-s1-bastion")
    question = next(q for q in module.questions if q.id == "q79")
    # q79 is the bastion resource-requirements question; option "b" is correct.
    assert fc.answer_text(question) == "8 vCPU, 16 GB memory, 80 GB disk"


def test_answer_text_joins_multi_select_answers(content_store):
    multi = [
        (m, q)
        for m in content_store.modules
        for q in m.questions
        if len(q.correct_set) > 1
    ]
    assert multi, "expected at least one multi-select question in content"
    module, question = multi[0]
    text = fc.answer_text(question)
    assert " · " in text
    assert len(text.split(" · ")) == len(question.correct_set)


def test_module_deck_only_contains_that_module(content_store):
    cards = fc.build_deck(content_store, module_id="ncpcn-s1-bastion")
    assert cards
    assert {c.module_id for c in cards} == {"ncpcn-s1-bastion"}


def test_track_deck_only_contains_that_track(content_store):
    track = content_store.tracks()[0]
    cards = fc.build_deck(content_store, track=track)
    assert cards
    assert {c.track for c in cards} == {track}


def test_parse_deck_id():
    assert fc.parse_deck_id("all") == (None, None)
    assert fc.parse_deck_id("module:abc") == ("abc", None)
    assert fc.parse_deck_id("track:NCP-CN Section 1") == (None, "NCP-CN Section 1")


def test_list_decks_covers_all_tracks_and_modules(content_store):
    decks = fc.list_decks(content_store)
    kinds = [d.kind for d in decks]
    assert kinds.count("all") == 1
    assert kinds.count("track") == len(content_store.tracks())
    assert kinds.count("module") == len(content_store.modules)
    # The "all" deck's count is the sum of every module's questions.
    all_deck = next(d for d in decks if d.kind == "all")
    assert all_deck.count == sum(len(m.questions) for m in content_store.modules)


# ---- API ----

@pytest.mark.asyncio
async def test_list_decks_endpoint(client):
    resp = await client.get("/api/flashcards/decks")
    assert resp.status_code == 200
    decks = resp.json()
    assert any(d["id"] == "all" for d in decks)
    assert all(d["count"] > 0 for d in decks)


@pytest.mark.asyncio
async def test_get_all_deck(client):
    resp = await client.get("/api/flashcards")
    assert resp.status_code == 200
    body = resp.json()
    assert body["deck_id"] == "all"
    assert body["count"] == len(body["cards"])
    card = body["cards"][0]
    assert card["front"] and card["back"] and card["answer"]


@pytest.mark.asyncio
async def test_get_module_deck(client):
    resp = await client.get("/api/flashcards", params={"deck_id": "module:ncpcn-s1-bastion"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] > 0
    assert {c["module_id"] for c in body["cards"]} == {"ncpcn-s1-bastion"}


@pytest.mark.asyncio
async def test_unknown_module_deck_404s(client):
    resp = await client.get("/api/flashcards", params={"deck_id": "module:does-not-exist"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_unknown_track_deck_404s(client):
    resp = await client.get("/api/flashcards", params={"deck_id": "track:Nope"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_flashcards_require_no_auth(client):
    """Decks are public self-study: no session token needed."""
    resp = await client.get("/api/flashcards", params={"deck_id": "all"})
    assert resp.status_code == 200
