"""Integration tests for the API: auth, content, quiz flow, progress, leaderboard."""
from __future__ import annotations


async def _login(client, username="tester"):
    resp = await client.post("/api/auth/login", json={"username": username})
    assert resp.status_code == 200
    return resp.json()["token"]


def _auth(token):
    return {"X-Session-Token": token}


async def test_healthz_ok(client):
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert resp.json()["modules_loaded"] >= 3


async def test_metrics_endpoint_exposes_prometheus(client):
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert "nkp_academy_http_requests_total" in resp.text


async def test_login_creates_user_and_me_roundtrip(client):
    token = await _login(client, "priya")
    resp = await client.get("/api/auth/me", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["username"] == "priya"


async def test_protected_route_requires_token(client):
    resp = await client.get("/api/progress")
    assert resp.status_code == 401


async def test_list_modules_hides_answers(client):
    resp = await client.get("/api/content/modules")
    assert resp.status_code == 200
    modules = resp.json()
    assert len(modules) >= 3
    detail = await client.get(f"/api/content/modules/{modules[0]['id']}")
    body = detail.json()
    # Questions must not leak correct answers or explanations pre-submission.
    for q in body["questions"]:
        assert "correct" not in q
        assert "explanation" not in q


async def test_answer_correct_awards_points_and_feedback(client, content_store):
    token = await _login(client, "diego")
    module = content_store.modules[0]
    question = module.questions[0]

    resp = await client.post(
        f"/api/quiz/{module.id}/answer",
        json={"question_id": question.id, "selected": list(question.correct)},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["correct"] is True
    assert body["points_awarded"] == question.points
    assert body["total_xp"] == question.points
    assert body["explanation"]  # feedback returned only after answering


async def test_answer_incorrect_awards_zero(client, content_store):
    token = await _login(client, "mei")
    module = content_store.modules[0]
    question = module.questions[0]
    wrong = [o.id for o in question.options if o.id not in question.correct_set][0]

    resp = await client.post(
        f"/api/quiz/{module.id}/answer",
        json={"question_id": question.id, "selected": [wrong]},
        headers=_auth(token),
    )
    body = resp.json()
    assert body["correct"] is False
    assert body["points_awarded"] == 0
    assert set(body["correct_options"]) == set(question.correct)


async def test_completing_a_module_awards_badge_and_updates_progress(client, content_store):
    token = await _login(client, "champion")
    module = content_store.modules[0]

    for question in module.questions:
        await client.post(
            f"/api/quiz/{module.id}/answer",
            json={"question_id": question.id, "selected": list(question.correct)},
            headers=_auth(token),
        )

    # A module-completion badge should have been awarded somewhere in the run.
    progress = (await client.get("/api/progress", headers=_auth(token))).json()
    completed = [m for m in progress["modules"] if m["module_id"] == module.id]
    assert completed and completed[0]["completed"] is True
    assert progress["total_xp"] == module.total_points
    assert len(progress["badges"]) >= 1


async def test_leaderboard_ranks_by_xp(client, content_store):
    module = content_store.modules[0]
    q = module.questions[0]

    # High scorer answers correctly; low scorer answers nothing.
    high = await _login(client, "highscore")
    await client.post(
        f"/api/quiz/{module.id}/answer",
        json={"question_id": q.id, "selected": list(q.correct)},
        headers=_auth(high),
    )
    await _login(client, "lowscore")

    board = (await client.get("/api/leaderboard")).json()
    usernames = [e["username"] for e in board["entries"]]
    assert "highscore" in usernames
    # highscore should outrank lowscore.
    if "lowscore" in usernames:
        assert usernames.index("highscore") < usernames.index("lowscore")
    assert board["entries"][0]["rank"] == 1
