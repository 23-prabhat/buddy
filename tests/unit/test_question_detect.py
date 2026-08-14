from bro.ai.reasoning.question_detect import QuestionDetector


def test_explicit_question():
    d = QuestionDetector().detect("Why did you choose XGBoost?", speaker="Speaker A")
    assert d.is_question
    assert d.directed_at_user


def test_implicit_request():
    d = QuestionDetector().detect(
        "Could you walk us through why you designed it this way?",
        speaker="Speaker B",
    )
    assert d.is_question
    assert d.directed_at_user


def test_user_speech_ignored():
    d = QuestionDetector().detect("Why is the sky blue?", speaker="User")
    assert not d.is_question


def test_statement_not_question():
    d = QuestionDetector().detect("We tried using XGBoost yesterday.", speaker="Speaker A")
    assert not d.is_question
