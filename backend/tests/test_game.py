"""Q&A game endpoint tests.

Covers: question serving (10-cap, no answers leaked, difficulty filter, slash
skills), scoring, the mastery flag, validation, and the anonymous-vs-logged-in
save behavior.
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select

from app import models
from app.routers.game import _claim_quiz
from app.utils import utcnow_naive


def _seed_questions(db, *, skill_name="Python", difficulty="easy", n=10, correct_index=0):
    """Seed one skill with n questions of a difficulty; option[0] is correct."""
    skill = db.scalar(select(models.Skill).where(models.Skill.skill_name == skill_name))
    if skill is None:
        skill = models.Skill(skill_name=skill_name)
        db.add(skill)
        db.flush()
    for i in range(n):
        q = models.Question(
            skill_id=skill.skill_id, difficulty=difficulty, question_text=f"Q{i}"
        )
        db.add(q)
        db.flush()
        for j in range(4):
            db.add(
                models.AnswerOption(
                    question_id=q.question_id,
                    option_text=f"opt{j}",
                    is_correct=(j == correct_index),
                )
            )
    db.commit()
    return skill


def _fetch_quiz(client, skill, difficulty, *, headers=None):
    return client.get(
        f"/game/{skill}", params={"difficulty": difficulty}, headers=headers or {}
    ).json()


def _play(client, skill, difficulty, *, headers=None, wrong=0):
    """Fetch a quiz and submit it; make `wrong` of the answers incorrect.

    Options come back shuffled, so the correct one is found by its seeded
    text ("opt0" when correct_index=0), not by position.
    """
    quiz = _fetch_quiz(client, skill, difficulty, headers=headers)
    answers = []
    for i, q in enumerate(quiz["questions"]):
        correct = next(o for o in q["options"] if o["option_text"] == "opt0")
        incorrect = next(o for o in q["options"] if o["option_text"] != "opt0")
        opt = incorrect if i < wrong else correct
        answers.append({"question_id": q["question_id"], "option_id": opt["option_id"]})
    return client.post(
        f"/game/{skill}/submit",
        json={
            "quiz_id": quiz["quiz_id"],
            "difficulty": difficulty,
            "answers": answers,
        },
        headers=headers or {},
    )


def _token(client, username="player"):
    client.post("/auth/register", json={"username": username, "password": "password123"})
    return client.post(
        "/auth/login", json={"username": username, "password": "password123"}
    ).json()["access_token"]


# --- serving questions -------------------------------------------------------

def test_options_are_shuffled(client, db_session):
    # One question, four options: over 20 fetches the first option must vary,
    # otherwise the correct answer's position leaks to the player.
    _seed_questions(db_session, n=1)
    first_option_ids = set()
    for _ in range(20):
        q = client.get("/game/Python", params={"difficulty": "easy"}).json()["questions"][0]
        first_option_ids.add(q["options"][0]["option_id"])
    assert len(first_option_ids) > 1


def test_get_returns_questions_without_answers(client, db_session):
    _seed_questions(db_session, n=10)
    r = client.get("/game/Python", params={"difficulty": "easy"})
    assert r.status_code == 200
    body = r.json()
    assert body["skill"] == "Python" and body["difficulty"] == "easy"
    assert "quiz_id" in body
    assert len(body["questions"]) == 10
    assert "is_correct" not in str(body)  # answers never leak to the client


def test_get_prunes_all_expired_quiz_sessions(client, db_session):
    skill = _seed_questions(db_session, n=1)
    old_time = utcnow_naive() - timedelta(hours=25)
    recent_time = utcnow_naive() - timedelta(hours=1)
    old_open = models.QuizSession(
        skill_id=skill.skill_id,
        difficulty="easy",
        question_ids="[]",
        completed=False,
        created_at=old_time,
    )
    old_completed = models.QuizSession(
        skill_id=skill.skill_id,
        difficulty="easy",
        question_ids="[]",
        completed=True,
        created_at=old_time,
    )
    recent_completed = models.QuizSession(
        skill_id=skill.skill_id,
        difficulty="easy",
        question_ids="[]",
        completed=True,
        created_at=recent_time,
    )
    db_session.add_all([old_open, old_completed, recent_completed])
    db_session.commit()
    old_ids = {old_open.session_id, old_completed.session_id}

    assert client.get("/game/Python", params={"difficulty": "easy"}).status_code == 200
    remaining = set(db_session.scalars(select(models.QuizSession.session_id)))
    assert remaining.isdisjoint(old_ids)
    assert recent_completed.session_id in remaining


def test_get_caps_at_ten(client, db_session):
    _seed_questions(db_session, n=15)
    assert len(client.get("/game/Python", params={"difficulty": "easy"}).json()["questions"]) == 10


def test_get_respects_difficulty(client, db_session):
    _seed_questions(db_session, difficulty="easy", n=4)
    _seed_questions(db_session, difficulty="hard", n=3)
    assert len(client.get("/game/Python", params={"difficulty": "hard"}).json()["questions"]) == 3


def test_get_unknown_skill_404(client, db_session):
    _seed_questions(db_session)
    assert client.get("/game/Nonsense", params={"difficulty": "easy"}).status_code == 404


def test_get_empty_bank_422(client, db_session):
    _seed_questions(db_session, difficulty="easy", n=5)  # skill exists, but no hard
    assert client.get("/game/Python", params={"difficulty": "hard"}).status_code == 422


def test_get_bad_difficulty_422(client, db_session):
    _seed_questions(db_session)
    assert client.get("/game/Python", params={"difficulty": "expert"}).status_code == 422


def test_get_slash_skill_routes(client, db_session):
    _seed_questions(db_session, skill_name="CI/CD", n=3)
    r = client.get("/game/CI/CD", params={"difficulty": "easy"})
    assert r.status_code == 200 and r.json()["skill"] == "CI/CD"


def test_list_quiz_skills(client, db_session):
    _seed_questions(db_session, skill_name="Python", difficulty="easy", n=2)
    _seed_questions(db_session, skill_name="Python", difficulty="hard", n=2)
    _seed_questions(db_session, skill_name="SQL", difficulty="easy", n=1)
    r = client.get("/game/skills")  # must route here, not to /{skill_name}
    assert r.status_code == 200
    by_skill = {row["skill"]: row["difficulties"] for row in r.json()}
    assert by_skill["Python"] == ["easy", "hard"]
    assert by_skill["SQL"] == ["easy"]


def test_list_quiz_skills_empty(client, db_session):
    assert client.get("/game/skills").json() == []


def test_skills_ignores_unknown_difficulty(client, db_session):
    _seed_questions(db_session, skill_name="Python", difficulty="easy", n=2)
    # a stray bad difficulty inserted directly, as if a seed typo slipped in
    bad = models.Skill(skill_name="Rust")
    db_session.add(bad)
    db_session.flush()
    db_session.add(
        models.Question(skill_id=bad.skill_id, difficulty="meduim", question_text="?")
    )
    db_session.commit()
    r = client.get("/game/skills")
    assert r.status_code == 200  # must not 500 on the bad value
    by_skill = {row["skill"]: row["difficulties"] for row in r.json()}
    assert by_skill["Python"] == ["easy"]
    assert "Rust" not in by_skill  # skill with only an invalid difficulty is dropped


# --- scoring + mastery -------------------------------------------------------

def test_submit_scores_all_correct(client, db_session):
    _seed_questions(db_session, difficulty="easy", n=10)
    body = _play(client, "Python", "easy").json()
    assert body["score"] == 10 and body["correct_count"] == 10 and body["max_score"] == 10
    assert len(body["results"]) == 10 and all(r["is_correct"] for r in body["results"])


def test_submit_partial_score(client, db_session):
    _seed_questions(db_session, difficulty="easy", n=10)
    body = _play(client, "Python", "easy", wrong=3).json()
    assert body["score"] == 7


def test_perfect_hard_is_mastered(client, db_session):
    _seed_questions(db_session, difficulty="hard", n=10)
    assert _play(client, "Python", "hard").json()["mastered"] is True


def test_imperfect_hard_not_mastered(client, db_session):
    _seed_questions(db_session, difficulty="hard", n=10)
    assert _play(client, "Python", "hard", wrong=1).json()["mastered"] is False


def test_perfect_easy_not_mastered(client, db_session):
    _seed_questions(db_session, difficulty="easy", n=10)
    assert _play(client, "Python", "easy").json()["mastered"] is False


# --- validation --------------------------------------------------------------

def _quiz_answers(client, skill, difficulty, count=None):
    """Fetch a quiz; return (quiz_id, answers picking each question's first option)."""
    quiz = _fetch_quiz(client, skill, difficulty)
    qs = quiz["questions"] if count is None else quiz["questions"][:count]
    answers = [
        {"question_id": q["question_id"], "option_id": q["options"][0]["option_id"]}
        for q in qs
    ]
    return quiz["quiz_id"], answers


def test_submit_incomplete_quiz_422(client, db_session):
    # quiz served 10 but only 3 answered -> reject (no partial-quiz "mastery")
    _seed_questions(db_session, difficulty="easy", n=10)
    quiz_id, answers = _quiz_answers(client, "Python", "easy", count=3)
    r = client.post(
        "/game/Python/submit",
        json={"quiz_id": quiz_id, "difficulty": "easy", "answers": answers},
    )
    assert r.status_code == 422


def test_submit_duplicate_question_422(client, db_session):
    _seed_questions(db_session, difficulty="easy", n=10)
    quiz_id, answers = _quiz_answers(client, "Python", "easy", count=1)
    r = client.post(
        "/game/Python/submit",
        json={"quiz_id": quiz_id, "difficulty": "easy", "answers": [answers[0], answers[0]]},
    )
    assert r.status_code == 422


def test_submit_option_not_on_question_422(client, db_session):
    _seed_questions(db_session, difficulty="easy", n=10)
    quiz_id, answers = _quiz_answers(client, "Python", "easy")
    answers[0]["option_id"] = 999999  # option that is not on that question
    r = client.post(
        "/game/Python/submit",
        json={"quiz_id": quiz_id, "difficulty": "easy", "answers": answers},
    )
    assert r.status_code == 422


def test_submit_foreign_question_422(client, db_session):
    _seed_questions(db_session, skill_name="Python", difficulty="easy", n=10)
    _seed_questions(db_session, skill_name="SQL", difficulty="easy", n=1)
    quiz_id, answers = _quiz_answers(client, "Python", "easy", count=9)
    _, foreign = _quiz_answers(client, "SQL", "easy", count=1)
    answers += foreign  # 10 total, one from another skill's quiz
    r = client.post(
        "/game/Python/submit",
        json={"quiz_id": quiz_id, "difficulty": "easy", "answers": answers},
    )
    assert r.status_code == 422


def test_submit_difficulty_mismatch_422(client, db_session):
    _seed_questions(db_session, difficulty="easy", n=10)
    quiz_id, answers = _quiz_answers(client, "Python", "easy")
    # claim hard while holding an easy quiz
    r = client.post(
        "/game/Python/submit",
        json={"quiz_id": quiz_id, "difficulty": "hard", "answers": answers},
    )
    assert r.status_code == 422


def test_submit_unknown_quiz_404(client, db_session):
    _seed_questions(db_session, difficulty="easy", n=10)
    _, answers = _quiz_answers(client, "Python", "easy")
    r = client.post(
        "/game/Python/submit",
        json={"quiz_id": 999999, "difficulty": "easy", "answers": answers},
    )
    assert r.status_code == 404


def test_quiz_cannot_be_submitted_twice(client, db_session):
    _seed_questions(db_session, difficulty="easy", n=10)
    quiz_id, answers = _quiz_answers(client, "Python", "easy")
    payload = {"quiz_id": quiz_id, "difficulty": "easy", "answers": answers}
    assert client.post("/game/Python/submit", json=payload).status_code == 200
    assert client.post("/game/Python/submit", json=payload).status_code == 409


def test_quiz_claim_is_atomic(client, db_session):
    _seed_questions(db_session, difficulty="easy", n=1)
    quiz_id, _ = _quiz_answers(client, "Python", "easy")
    assert _claim_quiz(db_session, quiz_id) is True
    assert _claim_quiz(db_session, quiz_id) is False


def test_consecutive_quizzes_avoid_repeats_for_user(client, db_session):
    # bank of 20: a logged-in player's second quiz shares zero questions
    _seed_questions(db_session, difficulty="easy", n=20)
    h = {"Authorization": f"Bearer {_token(client)}"}
    q1 = _fetch_quiz(client, "Python", "easy", headers=h)
    q2 = _fetch_quiz(client, "Python", "easy", headers=h)
    ids1 = {q["question_id"] for q in q1["questions"]}
    ids2 = {q["question_id"] for q in q2["questions"]}
    assert len(ids1) == 10 and len(ids2) == 10
    assert ids1.isdisjoint(ids2)


def test_other_users_quiz_403(client, db_session):
    _seed_questions(db_session, difficulty="easy", n=10)
    ha = {"Authorization": f"Bearer {_token(client, 'alice')}"}
    quiz = _fetch_quiz(client, "Python", "easy", headers=ha)
    answers = [
        {"question_id": q["question_id"], "option_id": q["options"][0]["option_id"]}
        for q in quiz["questions"]
    ]
    hb = {"Authorization": f"Bearer {_token(client, 'bobby')}"}
    r = client.post(
        "/game/Python/submit",
        json={"quiz_id": quiz["quiz_id"], "difficulty": "easy", "answers": answers},
        headers=hb,
    )
    assert r.status_code == 403


# --- save behavior -----------------------------------------------------------

def test_anonymous_submit_saves_nothing(client, db_session):
    _seed_questions(db_session, n=10)
    _play(client, "Python", "easy")
    assert db_session.scalar(select(func.count()).select_from(models.GameAttempt)) == 0


def test_logged_in_submit_saves_attempt(client, db_session):
    _seed_questions(db_session, n=10)
    token = _token(client)
    _play(client, "Python", "easy", headers={"Authorization": f"Bearer {token}"})
    attempts = db_session.scalars(select(models.GameAttempt)).all()
    assert len(attempts) == 1
    assert attempts[0].score == 10 and attempts[0].max_score == 10
    assert attempts[0].difficulty == "easy"


# --- normalized score / elapsed time ----------------------------------------


def test_submit_returns_normalized_score(client, db_session):
    """The 0..10000 display score comes from the server, not just the client.

    Keeps a stored attempt and the number the player saw from disagreeing.
    """
    _seed_questions(db_session, n=10)
    body = _play(client, "Python", "easy").json()

    assert body["score"] == 10
    assert body["score_normalized"] == 10_000


def test_normalized_score_scales_with_partial_score(client, db_session):
    _seed_questions(db_session, n=10)
    body = _play(client, "Python", "easy", wrong=4).json()

    assert body["score"] == 6
    assert body["score_normalized"] == 6_000


def test_submit_rejects_negative_elapsed_seconds(client, db_session):
    _seed_questions(db_session, n=3)
    quiz = _fetch_quiz(client, "Python", "easy")
    answers = [
        {
            "question_id": q["question_id"],
            "option_id": next(
                o for o in q["options"] if o["option_text"] == "opt0"
            )["option_id"],
        }
        for q in quiz["questions"]
    ]
    r = client.post(
        "/game/Python/submit",
        json={
            "quiz_id": quiz["quiz_id"],
            "difficulty": "easy",
            "answers": answers,
            "elapsed_seconds": -5,
        },
    )
    assert r.status_code == 422


def test_quiz_skills_is_cacheable(client, db_session):
    _seed_questions(db_session, n=1)
    assert "max-age" in client.get("/game/skills").headers["cache-control"]


def test_submit_reports_recorded_when_logged_in(client, db_session):
    _seed_questions(db_session, n=3)
    h = {"Authorization": f"Bearer {_token(client)}"}
    assert _play(client, "Python", "easy", headers=h).json()["recorded"] is True


def test_submit_reports_not_recorded_when_anonymous(client, db_session):
    """Anonymous play is graded but not saved, and now says so.

    A caller that forgot its Authorization header used to get a clean 200 and
    silently store nothing.
    """
    _seed_questions(db_session, n=3)
    body = _play(client, "Python", "easy").json()

    assert body["score"] == 3          # still graded
    assert body["recorded"] is False   # but not persisted


# --- running out of time -----------------------------------------------------


def _correct_option(question):
    return next(o for o in question["options"] if o["option_text"] == "opt0")["option_id"]


def test_timed_out_quiz_scores_what_was_answered(client, db_session):
    """Running out of time used to bin the attempt. Now it scores."""
    _seed_questions(db_session, n=10)
    quiz = _fetch_quiz(client, "Python", "easy")
    answers = [
        {"question_id": q["question_id"], "option_id": _correct_option(q)}
        for q in quiz["questions"][:6]          # only got through 6
    ]
    r = client.post(
        "/game/Python/submit",
        json={
            "quiz_id": quiz["quiz_id"],
            "difficulty": "easy",
            "answers": answers,
            "timed_out": True,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["score"] == 6
    assert body["max_score"] == 10           # still out of the whole quiz
    assert body["score_normalized"] == 6_000
    assert len(body["results"]) == 10        # the 4 unreached ones are reported
    assert sum(1 for x in body["results"] if not x["is_correct"]) == 4


def test_timed_out_cannot_beat_answering_everything(client, db_session):
    """Otherwise stopping early would be a way to farm a better percentage."""
    _seed_questions(db_session, n=10)
    quiz = _fetch_quiz(client, "Python", "easy")
    only_right_one = [
        {
            "question_id": quiz["questions"][0]["question_id"],
            "option_id": _correct_option(quiz["questions"][0]),
        }
    ]
    body = client.post(
        "/game/Python/submit",
        json={
            "quiz_id": quiz["quiz_id"],
            "difficulty": "easy",
            "answers": only_right_one,
            "timed_out": True,
        },
    ).json()
    # 1 of 10, not 1 of 1
    assert body["score"] == 1 and body["max_score"] == 10
    assert body["score_normalized"] == 1_000


def test_timed_out_hard_quiz_is_never_mastered(client, db_session):
    _seed_questions(db_session, difficulty="hard", n=10)
    quiz = _fetch_quiz(client, "Python", "hard")
    answers = [
        {"question_id": q["question_id"], "option_id": _correct_option(q)}
        for q in quiz["questions"][:9]
    ]
    body = client.post(
        "/game/Python/submit",
        json={
            "quiz_id": quiz["quiz_id"],
            "difficulty": "hard",
            "answers": answers,
            "timed_out": True,
        },
    ).json()
    assert body["score"] == 9
    assert body["mastered"] is False


def test_timed_out_counts_answers_already_graded_live(client, db_session):
    """The server knows what was answered, so the client need not resend it."""
    _seed_questions(db_session, n=10)
    quiz = _fetch_quiz(client, "Python", "easy")
    for i in range(3):
        _answer(client, "Python", quiz, i)          # graded live, then the page dies

    body = client.post(
        "/game/Python/submit",
        json={
            "quiz_id": quiz["quiz_id"],
            "difficulty": "easy",
            "answers": [],                          # client sent nothing
            "timed_out": True,
        },
    ).json()
    assert body["score"] == 3
    assert body["score_normalized"] == 3_000


def test_timed_out_still_rejects_a_foreign_question(client, db_session):
    _seed_questions(db_session, skill_name="Python", difficulty="easy", n=10)
    _seed_questions(db_session, skill_name="SQL", difficulty="easy", n=3)
    quiz = _fetch_quiz(client, "Python", "easy")
    other = _fetch_quiz(client, "SQL", "easy")
    r = client.post(
        "/game/Python/submit",
        json={
            "quiz_id": quiz["quiz_id"],
            "difficulty": "easy",
            "answers": [
                {
                    "question_id": other["questions"][0]["question_id"],
                    "option_id": other["questions"][0]["options"][0]["option_id"],
                }
            ],
            "timed_out": True,
        },
    )
    assert r.status_code == 422


def test_partial_quiz_without_the_timeout_flag_is_still_rejected(client, db_session):
    """The relaxation only applies when the client says the clock ran out."""
    _seed_questions(db_session, n=10)
    quiz_id, answers = _quiz_answers(client, "Python", "easy", count=3)
    r = client.post(
        "/game/Python/submit",
        json={"quiz_id": quiz_id, "difficulty": "easy", "answers": answers},
    )
    assert r.status_code == 422


def test_timed_out_records_the_attempt_for_a_logged_in_player(client, db_session):
    _seed_questions(db_session, n=10)
    h = {"Authorization": f"Bearer {_token(client)}"}
    quiz = _fetch_quiz(client, "Python", "easy", headers=h)
    answers = [
        {"question_id": q["question_id"], "option_id": _correct_option(q)}
        for q in quiz["questions"][:4]
    ]
    client.post(
        "/game/Python/submit",
        json={
            "quiz_id": quiz["quiz_id"],
            "difficulty": "easy",
            "answers": answers,
            "timed_out": True,
        },
        headers=h,
    )
    attempts = db_session.scalars(select(models.GameAttempt)).all()
    assert len(attempts) == 1
    assert attempts[0].score == 4 and attempts[0].max_score == 10


# --- per-answer grading (live points) ----------------------------------------


def _answer(client, skill, quiz, index, *, correct=True, headers=None, option_id=None):
    """Grade one answer of a fetched quiz through POST /game/{skill}/answer."""
    q = quiz["questions"][index]
    if option_id is None:
        picked = next(
            o for o in q["options"] if (o["option_text"] == "opt0") == correct
        )
        option_id = picked["option_id"]
    return client.post(
        f"/game/{skill}/answer",
        json={
            "quiz_id": quiz["quiz_id"],
            "question_id": q["question_id"],
            "option_id": option_id,
        },
        headers=headers or {},
    )


def test_answer_grades_a_correct_pick(client, db_session):
    _seed_questions(db_session, n=10)
    quiz = _fetch_quiz(client, "Python", "easy")
    body = _answer(client, "Python", quiz, 0).json()

    assert body["is_correct"] is True
    assert body["correct_count"] == 1
    assert body["answered_count"] == 1
    assert body["total_questions"] == 10
    assert body["quiz_complete"] is False


def test_answer_grades_a_wrong_pick(client, db_session):
    _seed_questions(db_session, n=10)
    quiz = _fetch_quiz(client, "Python", "easy")
    body = _answer(client, "Python", quiz, 0, correct=False).json()

    assert body["is_correct"] is False
    assert body["correct_count"] == 0
    assert body["score_normalized"] == 0


def test_answer_reveals_the_correct_option(client, db_session):
    """The page marks the right option, so it has to be told which one it is."""
    _seed_questions(db_session, n=10)
    quiz = _fetch_quiz(client, "Python", "easy")
    body = _answer(client, "Python", quiz, 0, correct=False).json()

    right = next(o for o in quiz["questions"][0]["options"] if o["option_text"] == "opt0")
    assert body["correct_option_id"] == right["option_id"]


def test_running_score_climbs_by_a_thousand_a_question(client, db_session):
    """One question is worth 1000 points, so the counter moves in 1000s."""
    _seed_questions(db_session, n=10)
    quiz = _fetch_quiz(client, "Python", "easy")

    assert _answer(client, "Python", quiz, 0).json()["score_normalized"] == 1_000
    assert _answer(client, "Python", quiz, 1).json()["score_normalized"] == 2_000
    # a miss does not move it
    assert _answer(client, "Python", quiz, 2, correct=False).json()["score_normalized"] == 2_000
    assert _answer(client, "Python", quiz, 3).json()["score_normalized"] == 3_000


def test_answer_locks_the_pick_so_a_retry_cannot_hunt_for_the_right_option(
    client, db_session
):
    """The whole point of grading server-side: no guess-until-it-says-correct."""
    _seed_questions(db_session, n=10)
    quiz = _fetch_quiz(client, "Python", "easy")
    first = _answer(client, "Python", quiz, 0, correct=False).json()
    assert first["is_correct"] is False

    retry = _answer(client, "Python", quiz, 0, correct=True).json()
    assert retry["already_answered"] is True
    assert retry["is_correct"] is False       # still the original wrong pick
    assert retry["correct_count"] == 0
    assert retry["answered_count"] == 1       # and it did not count twice


def test_answer_flags_the_last_question(client, db_session):
    _seed_questions(db_session, n=3)
    quiz = _fetch_quiz(client, "Python", "easy")
    assert _answer(client, "Python", quiz, 0).json()["quiz_complete"] is False
    assert _answer(client, "Python", quiz, 1).json()["quiz_complete"] is False
    assert _answer(client, "Python", quiz, 2).json()["quiz_complete"] is True


def test_live_score_matches_the_final_score(client, db_session):
    """The number the player watched climb must be the number they finish on."""
    _seed_questions(db_session, n=10)
    quiz = _fetch_quiz(client, "Python", "easy")
    answers = []
    live_total = 0
    for i in range(10):
        correct = i % 3 != 0          # 6 right, 4 wrong
        graded = _answer(client, "Python", quiz, i, correct=correct).json()
        live_total = graded["score_normalized"]
        answers.append(
            {
                "question_id": quiz["questions"][i]["question_id"],
                "option_id": next(
                    o["option_id"]
                    for o in quiz["questions"][i]["options"]
                    if (o["option_text"] == "opt0") == correct
                ),
            }
        )

    final = client.post(
        "/game/Python/submit",
        json={"quiz_id": quiz["quiz_id"], "difficulty": "easy", "answers": answers},
    ).json()

    assert live_total == 6_000
    assert final["score_normalized"] == live_total
    assert final["score"] == 6


def test_submit_cannot_swap_an_answer_that_was_graded_live(client, db_session):
    """Otherwise the live score and the recorded score could disagree."""
    _seed_questions(db_session, n=10)
    quiz = _fetch_quiz(client, "Python", "easy")
    _answer(client, "Python", quiz, 0, correct=False)

    # submit everything correct, including the question already graded wrong
    answers = [
        {
            "question_id": q["question_id"],
            "option_id": next(
                o for o in q["options"] if o["option_text"] == "opt0"
            )["option_id"],
        }
        for q in quiz["questions"]
    ]
    r = client.post(
        "/game/Python/submit",
        json={"quiz_id": quiz["quiz_id"], "difficulty": "easy", "answers": answers},
    )
    assert r.status_code == 409


def test_submit_fills_in_questions_that_were_never_graded_live(client, db_session):
    """A grading call lost to a bad connection must not cost the player anything."""
    _seed_questions(db_session, n=10)
    quiz = _fetch_quiz(client, "Python", "easy")
    _answer(client, "Python", quiz, 0)  # only one question graded live

    answers = [
        {
            "question_id": q["question_id"],
            "option_id": next(
                o for o in q["options"] if o["option_text"] == "opt0"
            )["option_id"],
        }
        for q in quiz["questions"]
    ]
    body = client.post(
        "/game/Python/submit",
        json={"quiz_id": quiz["quiz_id"], "difficulty": "easy", "answers": answers},
    ).json()
    assert body["score"] == 10


def test_answer_rejects_a_question_from_another_quiz(client, db_session):
    _seed_questions(db_session, skill_name="Python", difficulty="easy", n=10)
    _seed_questions(db_session, skill_name="SQL", difficulty="easy", n=3)
    quiz = _fetch_quiz(client, "Python", "easy")
    other = _fetch_quiz(client, "SQL", "easy")
    r = client.post(
        "/game/Python/answer",
        json={
            "quiz_id": quiz["quiz_id"],
            "question_id": other["questions"][0]["question_id"],
            "option_id": other["questions"][0]["options"][0]["option_id"],
        },
    )
    assert r.status_code == 422


def test_answer_rejects_an_option_from_another_question(client, db_session):
    _seed_questions(db_session, n=10)
    quiz = _fetch_quiz(client, "Python", "easy")
    foreign = quiz["questions"][1]["options"][0]["option_id"]
    r = _answer(client, "Python", quiz, 0, option_id=foreign)
    assert r.status_code == 422


def test_answer_rejects_a_submitted_quiz(client, db_session):
    _seed_questions(db_session, n=10)
    quiz = _fetch_quiz(client, "Python", "easy")
    answers = [
        {
            "question_id": q["question_id"],
            "option_id": next(
                o for o in q["options"] if o["option_text"] == "opt0"
            )["option_id"],
        }
        for q in quiz["questions"]
    ]
    client.post(
        "/game/Python/submit",
        json={"quiz_id": quiz["quiz_id"], "difficulty": "easy", "answers": answers},
    )
    assert _answer(client, "Python", quiz, 0).status_code == 409


def test_answer_rejects_another_players_quiz(client, db_session):
    _seed_questions(db_session, n=10)
    ha = {"Authorization": f"Bearer {_token(client, 'alice')}"}
    quiz = _fetch_quiz(client, "Python", "easy", headers=ha)
    hb = {"Authorization": f"Bearer {_token(client, 'bobby')}"}
    assert _answer(client, "Python", quiz, 0, headers=hb).status_code == 403


def test_answer_unknown_quiz_404(client, db_session):
    _seed_questions(db_session, n=10)
    quiz = _fetch_quiz(client, "Python", "easy")
    r = client.post(
        "/game/Python/answer",
        json={
            "quiz_id": 999999,
            "question_id": quiz["questions"][0]["question_id"],
            "option_id": quiz["questions"][0]["options"][0]["option_id"],
        },
    )
    assert r.status_code == 404


def test_answer_works_for_anonymous_players(client, db_session):
    """Anonymous play is supported, so live points have to work without a token."""
    _seed_questions(db_session, n=10)
    quiz = _fetch_quiz(client, "Python", "easy")
    assert _answer(client, "Python", quiz, 0).json()["is_correct"] is True


def test_answer_routes_for_a_slash_skill(client, db_session):
    """"CI/CD" must not be swallowed by the /submit or /{skill} routes."""
    _seed_questions(db_session, skill_name="CI/CD", n=3)
    quiz = _fetch_quiz(client, "CI/CD", "easy")
    assert _answer(client, "CI/CD", quiz, 0).status_code == 200


def test_submit_rejects_an_oversized_answer_list(client, db_session):
    """Bound the list before the exact-question-set check parses all of it."""
    _seed_questions(db_session, n=3)
    quiz = _fetch_quiz(client, "Python", "easy")
    answers = [{"question_id": 1, "option_id": 1} for _ in range(500)]
    r = client.post(
        "/game/Python/submit",
        json={
            "quiz_id": quiz["quiz_id"],
            "difficulty": "easy",
            "answers": answers,
        },
    )
    assert r.status_code == 422
