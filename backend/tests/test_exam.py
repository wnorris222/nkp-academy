"""Tests for practice-exam sampling and grading (pure logic + API)."""
from __future__ import annotations

import random

from app import exam

# ---- pure sampling ----

def test_build_exam_respects_count(content_store):
    items = exam.build_exam(content_store, 50, rng=random.Random(1))
    assert len(items) == 50


def test_build_exam_spans_all_tracks(content_store):
    # A 40-question exam should draw from every section/track.
    items = exam.build_exam(content_store, 40, rng=random.Random(2))
    tracks_hit = {it.track for it in items}
    assert tracks_hit == set(content_store.tracks())


def test_build_exam_no_duplicate_questions(content_store):
    items = exam.build_exam(content_store, 60, rng=random.Random(3))
    keys = [(it.module_id, it.question.id) for it in items]
    assert len(keys) == len(set(keys))


def test_build_exam_track_filter(content_store):
    target = content_store.tracks()[0]
    items = exam.build_exam(content_store, 20, tracks=[target], rng=random.Random(4))
    assert {it.track for it in items} == {target}


def test_build_exam_caps_at_pool_size(content_store):
    total = sum(len(m.questions) for m in content_store.modules)
    items = exam.build_exam(content_store, total + 500, rng=random.Random(5))
    assert len(items) == total


def test_build_exam_is_deterministic_with_seed(content_store):
    a = exam.build_exam(content_store, 30, rng=random.Random(42))
    b = exam.build_exam(content_store, 30, rng=random.Random(42))
    assert [(i.module_id, i.question.id) for i in a] == [
        (i.module_id, i.question.id) for i in b
    ]


# ---- grading ----

def test_grade_exam_all_correct_passes(content_store):
    items = exam.build_exam(content_store, 20, rng=random.Random(7))
    subs = [
        (it.module_id, it.question.id, list(it.question.correct)) for it in items
    ]
    report = exam.grade_exam(content_store, subs, pass_threshold=0.75)
    assert report.total == 20
    assert report.correct == 20
    assert report.score_pct == 1.0
    assert report.passed is True
    # Section totals sum back to the exam size.
    assert sum(s.total for s in report.sections) == 20


def test_grade_exam_all_wrong_fails(content_store):
    items = exam.build_exam(content_store, 12, rng=random.Random(8))
    subs = [(it.module_id, it.question.id, []) for it in items]  # unanswered
    report = exam.grade_exam(content_store, subs, pass_threshold=0.75)
    assert report.correct == 0
    assert report.answered == 0
    assert report.passed is False
    assert report.score_pct == 0.0


def test_grade_exam_threshold_boundary(content_store):
    items = exam.build_exam(content_store, 10, rng=random.Random(9))
    subs = []
    for i, it in enumerate(items):
        # Answer 8/10 correctly -> 80% >= 75% passes.
        sel = list(it.question.correct) if i < 8 else ["__wrong__"]
        subs.append((it.module_id, it.question.id, sel))
    report = exam.grade_exam(content_store, subs, pass_threshold=0.75)
    assert report.correct == 8
    assert report.score_pct == 0.8
    assert report.passed is True


def test_grade_exam_skips_unknown_refs(content_store):
    subs = [("no-such-module", "q1", ["a"])]
    report = exam.grade_exam(content_store, subs, pass_threshold=0.75)
    assert report.total == 0


# ---- API ----

async def test_generate_exam_hides_answers(client):
    resp = await client.get("/api/exam?count=30")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 30
    assert body["pass_threshold"] == 0.75
    tracks = {q["track"] for q in body["questions"]}
    assert len(tracks) >= 2  # spans multiple sections
    for q in body["questions"]:
        assert "correct" not in q
        assert "explanation" not in q


async def test_submit_exam_returns_scored_report(client):
    gen = (await client.get("/api/exam?count=15")).json()
    # Fetch each module once to learn correct answers, then answer all correctly.
    answers = []
    for q in gen["questions"]:
        detail = (await client.get(f"/api/content/modules/{q['module_id']}")).json()
        # We don't get correct answers from content API; submit blank and rely on
        # the report to grade. Instead, submit the option we can't verify — so we
        # just check the report shape and section coverage here.
        answers.append(
            {"module_id": q["module_id"], "question_id": q["question_id"], "selected": []}
        )
        assert detail["id"] == q["module_id"]
    resp = await client.post("/api/exam/submit", json={"answers": answers})
    assert resp.status_code == 200
    report = resp.json()
    assert report["total"] == 15
    assert report["answered"] == 0
    assert 0.0 <= report["score_pct"] <= 1.0
    assert sum(s["total"] for s in report["sections"]) == 15
    assert len(report["results"]) == 15
