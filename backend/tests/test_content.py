"""Tests that validate the shipped YAML content is well-formed and consistent."""
from __future__ import annotations


def test_at_least_three_modules(content_store):
    assert len(content_store.modules) >= 3


def test_at_least_fifteen_questions(content_store):
    total = sum(len(m.questions) for m in content_store.modules)
    assert total >= 15


def test_every_question_correct_answer_is_a_valid_option(content_store):
    for module in content_store.modules:
        for q in module.questions:
            option_ids = {o.id for o in q.options}
            assert q.correct_set, f"{module.id}/{q.id} has no correct answer"
            assert q.correct_set <= option_ids, (
                f"{module.id}/{q.id} correct answer references unknown option"
            )


def test_question_ids_unique_within_module(content_store):
    for module in content_store.modules:
        ids = [q.id for q in module.questions]
        assert len(ids) == len(set(ids)), f"duplicate question id in {module.id}"


def test_module_ids_unique(content_store):
    ids = [m.id for m in content_store.modules]
    assert len(ids) == len(set(ids))


def test_question_types_are_supported(content_store):
    allowed = {"multiple_choice", "true_false", "scenario"}
    for module in content_store.modules:
        for q in module.questions:
            assert q.type in allowed, f"{module.id}/{q.id} has unsupported type {q.type}"


def test_badge_criteria_reference_real_targets(content_store):
    module_ids = {m.id for m in content_store.modules}
    tracks = set(content_store.tracks())
    for badge in content_store.badges:
        if badge.criteria_type == "module_complete":
            assert badge.criteria_value in module_ids
        elif badge.criteria_type == "track_complete":
            assert badge.criteria_value in tracks
        elif badge.criteria_type == "xp_threshold":
            assert badge.criteria_value.isdigit()
