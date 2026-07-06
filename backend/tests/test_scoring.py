"""Unit tests for the pure scoring/XP/badge logic (no DB, no I/O)."""
from __future__ import annotations

import pytest

from app.content import Badge, ContentStore, Module, Option, Question
from app.scoring import (
    evaluate_badges,
    grade_answer,
    level_for_xp,
    score_module,
    xp_to_next_level,
)


def _q(qid: str, correct, points: int = 10, qtype: str = "multiple_choice") -> Question:
    return Question(
        id=qid,
        type=qtype,
        prompt="?",
        options=(Option("a", "A"), Option("b", "B"), Option("c", "C")),
        correct=tuple(correct) if isinstance(correct, list | tuple) else (correct,),
        explanation="because",
        points=points,
    )


# ---- grade_answer ----

def test_correct_single_answer_awards_full_points():
    q = _q("q1", "b", points=15)
    result = grade_answer(q, ["b"])
    assert result.correct is True
    assert result.points_awarded == 15
    assert result.explanation == "because"


def test_incorrect_answer_awards_zero():
    q = _q("q1", "b")
    result = grade_answer(q, ["a"])
    assert result.correct is False
    assert result.points_awarded == 0


def test_multi_select_requires_exact_match():
    q = _q("q1", ["a", "c"], points=20)
    assert grade_answer(q, ["a", "c"]).correct is True
    assert grade_answer(q, ["c", "a"]).correct is True  # order-independent
    assert grade_answer(q, ["a"]).correct is False       # incomplete
    assert grade_answer(q, ["a", "b", "c"]).correct is False  # superset


def test_true_false_grading():
    q = _q("tf", "true", qtype="true_false")
    assert grade_answer(q, ["true"]).correct is True
    assert grade_answer(q, ["false"]).correct is False


def test_correct_options_are_reported_sorted():
    q = _q("q1", ["c", "a"])
    result = grade_answer(q, ["a", "c"])
    assert result.correct_options == ("a", "c")


# ---- score_module ----

def _module(qs) -> Module:
    return Module(
        id="m1", title="M1", track="T", order=1, summary="", icon="x", questions=tuple(qs)
    )


def test_score_module_completed_only_when_all_correct():
    qs = [_q("q1", "a"), _q("q2", "b")]
    module = _module(qs)
    graded = [grade_answer(qs[0], ["a"]), grade_answer(qs[1], ["b"])]
    score = score_module(module, graded)
    assert score.correct == 2
    assert score.xp == 20
    assert score.completed is True
    assert score.accuracy == 1.0


def test_score_module_incomplete_when_missing_answers():
    qs = [_q("q1", "a"), _q("q2", "b")]
    module = _module(qs)
    graded = [grade_answer(qs[0], ["a"])]  # only one answered
    score = score_module(module, graded)
    assert score.completed is False
    assert score.xp == 10


def test_empty_module_never_completed():
    module = _module([])
    assert score_module(module, []).completed is False


# ---- levels ----

@pytest.mark.parametrize(
    "xp,expected_level",
    [(0, 1), (99, 1), (100, 2), (299, 2), (300, 3), (600, 4)],
)
def test_level_for_xp(xp, expected_level):
    assert level_for_xp(xp) == expected_level


def test_xp_to_next_level():
    assert xp_to_next_level(0) == 100     # need 100 to reach level 2
    assert xp_to_next_level(100) == 200   # level 2 -> 3 costs 200
    assert xp_to_next_level(250) == 50    # 50 more to hit 300 (level 3)


# ---- badges ----

def _store_with_badges() -> ContentStore:
    modules = (
        Module("m1", "M1", "Track A", 1, "", "x", (_q("q1", "a"),)),
        Module("m2", "M2", "Track A", 2, "", "x", (_q("q2", "b"),)),
    )
    badges = (
        Badge("b-mod", "Mod", "", "x", "module_complete", "m1"),
        Badge("b-track", "Track", "", "x", "track_complete", "Track A"),
        Badge("b-xp", "XP", "", "x", "xp_threshold", "100"),
    )
    return ContentStore(modules=modules, badges=badges)


def test_module_complete_badge_awarded():
    store = _store_with_badges()
    newly = evaluate_badges(store, completed_module_ids={"m1"}, total_xp=10, already_earned=set())
    assert {b.id for b in newly} == {"b-mod"}


def test_track_complete_requires_all_modules():
    store = _store_with_badges()
    # Only m1 done -> no track badge yet.
    newly = evaluate_badges(store, {"m1"}, total_xp=10, already_earned=set())
    assert "b-track" not in {b.id for b in newly}
    # Both modules done -> track badge unlocks.
    newly = evaluate_badges(store, {"m1", "m2"}, total_xp=10, already_earned=set())
    assert "b-track" in {b.id for b in newly}


def test_xp_threshold_badge():
    store = _store_with_badges()
    newly = evaluate_badges(store, set(), total_xp=150, already_earned=set())
    assert "b-xp" in {b.id for b in newly}


def test_already_earned_badges_are_not_reissued():
    store = _store_with_badges()
    newly = evaluate_badges(store, {"m1"}, total_xp=10, already_earned={"b-mod"})
    assert newly == []
