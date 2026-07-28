"""Seed loader tests: re-running must refresh dates and never duplicate rows."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app import models


def _run_question_seed(tmp_path, monkeypatch, questions, prune=False):
    import app.seed_questions as sq

    fixture = tmp_path / "questions.json"
    fixture.write_text(json.dumps({"questions": questions}))
    engine = create_engine(
        f"sqlite:///{tmp_path / 'q.db'}", connect_args={"check_same_thread": False}
    )
    Session = sessionmaker(bind=engine)
    monkeypatch.setattr(sq, "engine", engine)
    monkeypatch.setattr(sq, "SessionLocal", Session)
    monkeypatch.setattr(sq, "FIXTURE", fixture)
    sq.seed_questions(prune=prune)
    return Session


def _banks(Session):
    """{(skill_name, difficulty): question count} currently in the database."""
    with Session() as s:
        rows = s.execute(
            select(
                models.Skill.skill_name,
                models.Question.difficulty,
                func.count(models.Question.question_id),
            )
            .join(models.Question, models.Question.skill_id == models.Skill.skill_id)
            .group_by(models.Skill.skill_name, models.Question.difficulty)
        ).all()
    return {(name, diff): n for name, diff, n in rows}


def test_seed_questions_rejects_invalid_difficulty(tmp_path, monkeypatch):
    with pytest.raises(ValueError):
        _run_question_seed(
            tmp_path,
            monkeypatch,
            [
                {
                    "skill": "Python",
                    "difficulty": "meduim",  # typo
                    "question_text": "?",
                    "options": [
                        {"text": "a", "correct": True},
                        {"text": "b", "correct": False},
                    ],
                }
            ],
        )


def test_seed_questions_rejects_zero_correct_options(tmp_path, monkeypatch):
    with pytest.raises(ValueError):
        _run_question_seed(
            tmp_path,
            monkeypatch,
            [
                {
                    "skill": "Python",
                    "difficulty": "easy",
                    "question_text": "?",
                    "options": [
                        {"text": "a", "correct": False},
                        {"text": "b", "correct": False},
                    ],
                }
            ],
        )


def test_seed_questions_rejects_multiple_correct_options(tmp_path, monkeypatch):
    with pytest.raises(ValueError):
        _run_question_seed(
            tmp_path,
            monkeypatch,
            [
                {
                    "skill": "Python",
                    "difficulty": "easy",
                    "question_text": "?",
                    "options": [
                        {"text": "a", "correct": True},
                        {"text": "b", "correct": True},
                    ],
                }
            ],
        )


def _q(skill="Python", difficulty="easy", text="?", options=None):
    if options is None:
        options = [{"text": "a", "correct": True}, {"text": "b", "correct": False}]
    return {
        "skill": skill,
        "difficulty": difficulty,
        "question_text": text,
        "options": options,
    }


def test_seed_questions_rejects_empty_text(tmp_path, monkeypatch):
    with pytest.raises(ValueError):
        _run_question_seed(tmp_path, monkeypatch, [_q(text="   ")])


def test_seed_questions_rejects_duplicate_option_text(tmp_path, monkeypatch):
    with pytest.raises(ValueError):
        _run_question_seed(
            tmp_path,
            monkeypatch,
            [_q(options=[{"text": "a", "correct": True}, {"text": "a", "correct": False}])],
        )


def test_seed_questions_rejects_duplicate_question_in_bank(tmp_path, monkeypatch):
    with pytest.raises(ValueError):
        _run_question_seed(
            tmp_path,
            monkeypatch,
            [_q(text="Same one?"), _q(text="Same one?")],
        )


@pytest.mark.parametrize(
    "first, second",
    [
        # The nine pairs that got through in practice all differed like this.
        ('What is a "sprint" in Scrum?', "What is a 'sprint' in Scrum?"),
        ("What is a merge conflict and when does it occur?",
         "What is a merge conflict, and when does it occur?"),
        ("What does REST stand for?", 'What does "REST" stand for?'),
        ("What is a Kubernetes Node?", "What is a Kubernetes 'Node'?"),
        ("What is the purpose of a daily standup meeting?",
         "What is the purpose of a daily stand-up meeting?"),
    ],
)
def test_seed_rejects_a_question_that_is_only_reworded(
    tmp_path, monkeypatch, first, second
):
    """Punctuation is not a difference worth keeping two questions over.

    Matching on raw text let these pairs into the bank, and a ten-question run
    drawn from fifteen showed the player the same question twice.
    """
    with pytest.raises(ValueError):
        _run_question_seed(tmp_path, monkeypatch, [_q(text=first), _q(text=second)])


def test_seed_still_allows_genuinely_different_questions(tmp_path, monkeypatch):
    # The normalising must not be so loose it collapses distinct questions.
    _run_question_seed(
        tmp_path,
        monkeypatch,
        [_q(text="What is a pod?"), _q(text="What is a node?")],
    )


def test_seed_error_names_the_offending_question(tmp_path, monkeypatch):
    # error text should locate the bad row by skill/difficulty, not just index
    with pytest.raises(ValueError, match="SQL"):
        _run_question_seed(
            tmp_path,
            monkeypatch,
            [_q(), _q(skill="SQL", difficulty="wrong")],
        )


def test_seed_allows_same_text_across_different_banks(tmp_path, monkeypatch):
    # a shared stem in easy vs hard (or across skills) is not a duplicate
    _run_question_seed(
        tmp_path,
        monkeypatch,
        [_q(text="What is it?"), _q(difficulty="hard", text="What is it?")],
    )


def _count(Session):
    with Session() as s:
        total = s.scalar(select(func.count()).select_from(models.JobPosting))
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
        fresh = s.scalar(
            select(func.count())
            .select_from(models.JobPosting)
            .where(models.JobPosting.date_posted >= cutoff)
        )
    return total, fresh


def test_seed_rerun_refreshes_without_duplicating(tmp_path, monkeypatch):
    import app.seed as seedmod

    engine = create_engine(
        f"sqlite:///{tmp_path / 'seed.db'}",
        connect_args={"check_same_thread": False},
    )
    Session = sessionmaker(bind=engine)
    monkeypatch.setattr(seedmod, "engine", engine)
    monkeypatch.setattr(seedmod, "SessionLocal", Session)

    seedmod.seed()
    total1, fresh1 = _count(Session)
    assert total1 > 0
    assert fresh1 == total1  # first load: everything fresh

    seedmod.seed()  # re-run
    total2, fresh2 = _count(Session)
    assert total2 == total1  # no duplication (dedup on external_id)
    assert fresh2 == total2  # re-run re-stamped every posting inside 30 days


def test_prune_removes_banks_the_fixture_dropped(tmp_path, monkeypatch):
    """A skill deleted from the fixture must stop being offered.

    Without pruning the reload only clears banks it is about to rewrite, so
    the dropped skill's questions survive and /game/skills keeps advertising
    a quiz the fixture no longer defines.
    """
    _run_question_seed(
        tmp_path, monkeypatch, [_q(skill="Python"), _q(skill="SQL")], prune=True
    )
    Session = _run_question_seed(
        tmp_path, monkeypatch, [_q(skill="Python")], prune=True
    )

    assert _banks(Session) == {("Python", "easy"): 1}


def test_prune_keeps_banks_the_fixture_still_has(tmp_path, monkeypatch):
    _run_question_seed(
        tmp_path,
        monkeypatch,
        [_q(skill="Python"), _q(skill="Python", difficulty="hard")],
        prune=True,
    )
    Session = _run_question_seed(
        tmp_path,
        monkeypatch,
        [_q(skill="Python"), _q(skill="Python", difficulty="hard")],
        prune=True,
    )

    assert _banks(Session) == {("Python", "easy"): 1, ("Python", "hard"): 1}


def test_without_prune_a_partial_fixture_leaves_other_banks_alone(tmp_path, monkeypatch):
    """The CLI loader stays additive so you can load one skill on its own."""
    _run_question_seed(tmp_path, monkeypatch, [_q(skill="Python"), _q(skill="SQL")])
    Session = _run_question_seed(tmp_path, monkeypatch, [_q(skill="Python")])

    assert _banks(Session) == {("Python", "easy"): 1, ("SQL", "easy"): 1}


def test_prune_removes_orphaned_answer_options(tmp_path, monkeypatch):
    """Options must go with their questions, not linger as orphans."""
    _run_question_seed(
        tmp_path, monkeypatch, [_q(skill="Python"), _q(skill="SQL")], prune=True
    )
    Session = _run_question_seed(
        tmp_path, monkeypatch, [_q(skill="Python")], prune=True
    )

    with Session() as s:
        options = s.scalar(select(func.count()).select_from(models.AnswerOption))
        questions = s.scalar(select(func.count()).select_from(models.Question))
    assert questions == 1
    assert options == 2


def test_seed_questions_names_the_entry_missing_a_skill(tmp_path, monkeypatch):
    """A bank with no skill must name the entry, not raise a bare KeyError.

    Every other validation failure names the offending question; this one used
    to surface as KeyError('skill') with no indication of which entry was bad.
    """
    with pytest.raises(ValueError) as exc:
        _run_question_seed(
            tmp_path,
            monkeypatch,
            [
                {
                    "difficulty": "easy",
                    "question_text": "What is a list?",
                    "options": [
                        {"text": "a", "correct": True},
                        {"text": "b", "correct": False},
                    ],
                }
            ],
        )
    assert "skill" in str(exc.value).lower()


def test_seed_questions_rejects_blank_skill(tmp_path, monkeypatch):
    with pytest.raises(ValueError):
        _run_question_seed(
            tmp_path,
            monkeypatch,
            [
                {
                    "skill": "   ",
                    "difficulty": "easy",
                    "question_text": "?",
                    "options": [
                        {"text": "a", "correct": True},
                        {"text": "b", "correct": False},
                    ],
                }
            ],
        )
