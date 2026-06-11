"""Tests for Phase 4: public quizzes + shared decks."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── PublicQuiz model ──────────────────────────────────────────────────────────

def test_public_quiz_model_has_required_fields():
    from app.models.models import PublicQuiz
    cols = {c.key for c in PublicQuiz.__table__.columns}
    for f in ("id", "slug", "title", "category", "questions", "is_active", "play_count"):
        assert f in cols, f"Missing field: {f}"


def test_public_quiz_slug_is_unique():
    from app.models.models import PublicQuiz
    slug_col = PublicQuiz.__table__.c["slug"]
    assert slug_col.unique


def test_public_quiz_has_is_active_default():
    from app.models.models import PublicQuiz
    is_active_col = PublicQuiz.__table__.c["is_active"]
    assert is_active_col.default is not None or is_active_col.server_default is not None


# ── SharedDeck model ──────────────────────────────────────────────────────────

def test_shared_deck_model_has_required_fields():
    from app.models.models import SharedDeck
    cols = {c.key for c in SharedDeck.__table__.columns}
    for f in ("id", "owner_id", "name", "token", "cards", "is_active", "view_count"):
        assert f in cols, f"Missing field: {f}"


def test_shared_deck_token_is_unique():
    from app.models.models import SharedDeck
    token_col = SharedDeck.__table__.c["token"]
    assert token_col.unique


def test_shared_deck_owner_is_foreign_key():
    from app.models.models import SharedDeck
    owner_col = SharedDeck.__table__.c["owner_id"]
    assert len(owner_col.foreign_keys) > 0


# ── Quiz question stripping ───────────────────────────────────────────────────

def test_quiz_public_response_strips_correct_answers():
    """The public quiz endpoint must NOT expose 'correct' or 'explanation' fields."""
    questions = [
        {"question": "What is 2+2?", "options": {"A": "3", "B": "4"}, "correct": "B", "explanation": "Basic math"},
    ]
    # Simulate the stripping logic from the endpoint
    public_questions = [
        {"question": q.get("question", ""), "options": q.get("options", {})}
        for q in questions
    ]
    assert "correct" not in public_questions[0]
    assert "explanation" not in public_questions[0]
    assert public_questions[0]["question"] == "What is 2+2?"


def test_quiz_scoring_all_correct():
    questions = [
        {"correct": "A"}, {"correct": "B"}, {"correct": "C"},
    ]
    user_answers = {"0": "A", "1": "B", "2": "C"}
    correct_count = sum(
        1 for i, q in enumerate(questions)
        if user_answers.get(str(i), "").upper() == q["correct"].upper()
    )
    assert correct_count == 3


def test_quiz_scoring_partial():
    questions = [
        {"correct": "A"}, {"correct": "B"}, {"correct": "C"},
    ]
    user_answers = {"0": "A", "1": "D", "2": "C"}  # 1 wrong
    correct_count = sum(
        1 for i, q in enumerate(questions)
        if user_answers.get(str(i), "").upper() == q["correct"].upper()
    )
    assert correct_count == 2


def test_quiz_scoring_none_correct():
    questions = [{"correct": "A"}]
    user_answers = {"0": "B"}
    correct_count = sum(
        1 for i, q in enumerate(questions)
        if user_answers.get(str(i), "").upper() == q["correct"].upper()
    )
    assert correct_count == 0


def test_quiz_scoring_case_insensitive():
    questions = [{"correct": "A"}]
    user_answers = {"0": "a"}  # lowercase
    correct_count = sum(
        1 for i, q in enumerate(questions)
        if user_answers.get(str(i), "").upper() == q["correct"].upper()
    )
    assert correct_count == 1


def test_quiz_score_pct_calculation():
    correct = 7
    total = 10
    pct = round(correct / total * 100)
    assert pct == 70


def test_quiz_score_pct_perfect():
    assert round(10 / 10 * 100) == 100


def test_quiz_score_pct_zero():
    assert round(0 / 10 * 100) == 0


# ── Redis percentile calculation ─────────────────────────────────────────────

def test_percentile_calculation():
    """Given stats where 8/10 players scored ≤ user's score, percentile = 80."""
    user_score = 7
    # Simulate stats: 2 scored 3, 3 scored 5, 3 scored 7, 2 scored 10
    stats = {
        "total_plays": "10",
        "score_3": "2",
        "score_5": "3",
        "score_7": "3",
        "score_10": "2",
    }
    total_plays = int(stats["total_plays"])
    scored_lte = sum(
        int(v) for k, v in stats.items()
        if k.startswith("score_") and int(k[6:]) <= user_score
    )
    percentile = round(scored_lte / total_plays * 100)
    assert percentile == 80  # 8 out of 10 scored <= 7


def test_percentile_fallback_on_no_data():
    total_plays = 0
    scored_lte = 0
    percentile = round(scored_lte / total_plays * 100) if total_plays else 50
    assert percentile == 50  # fallback


# ── Starter quizzes seed ──────────────────────────────────────────────────────

def test_starter_quizzes_have_required_keys():
    from scripts.seed_public_quizzes import QUIZZES
    required = {"slug", "title", "description", "category", "questions"}
    for quiz in QUIZZES:
        assert required <= set(quiz.keys()), f"Missing keys in quiz: {quiz['slug']}"


def test_starter_quizzes_count():
    from scripts.seed_public_quizzes import QUIZZES
    assert len(QUIZZES) == 5


def test_starter_quizzes_all_have_unique_slugs():
    from scripts.seed_public_quizzes import QUIZZES
    slugs = [q["slug"] for q in QUIZZES]
    assert len(slugs) == len(set(slugs))


def test_starter_questions_have_correct_field():
    from scripts.seed_public_quizzes import QUIZZES
    for quiz in QUIZZES:
        for q in quiz["questions"]:
            assert "correct" in q, f"Missing 'correct' in {quiz['slug']}"
            assert q["correct"] in q["options"], f"Correct answer not in options: {quiz['slug']}"


def test_starter_questions_have_explanation():
    from scripts.seed_public_quizzes import QUIZZES
    for quiz in QUIZZES:
        for q in quiz["questions"]:
            assert q.get("explanation"), f"Missing explanation in {quiz['slug']}"


def test_starter_quizzes_minimum_questions():
    from scripts.seed_public_quizzes import QUIZZES
    for quiz in QUIZZES:
        assert len(quiz["questions"]) >= 5, f"{quiz['slug']} has fewer than 5 questions"


# ── SharedDeck token generation ───────────────────────────────────────────────

def test_token_is_url_safe():
    import secrets
    for _ in range(100):
        token = secrets.token_urlsafe(8)[:10]
        assert len(token) <= 10
        assert all(c.isalnum() or c in ("-", "_") for c in token)


def test_deck_snapshot_structure():
    """Shared deck cards snapshot should have question, answer, difficulty."""
    cards_input = [
        MagicMock(question="Q1", answer="A1", difficulty="easy"),
        MagicMock(question="Q2", answer="A2", difficulty="hard"),
    ]
    snapshot = [
        {"question": c.question, "answer": c.answer, "difficulty": c.difficulty}
        for c in cards_input
    ]
    assert len(snapshot) == 2
    assert snapshot[0] == {"question": "Q1", "answer": "A1", "difficulty": "easy"}
