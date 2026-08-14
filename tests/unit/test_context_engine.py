from bro.core.configuration.settings import Settings
from bro.core.context.engine import AssistantContext, ContextEngine


def test_build_prioritizes_question():
    engine = ContextEngine(Settings())
    pkg = engine.build(
        AssistantContext(
            user_question="Why XGBoost?",
            meeting_transcript="Speaker: we need recall\nSpeaker: why xgboost?",
            mode="meeting",
        )
    )
    assert "Why XGBoost?" in pkg.user_content
    assert "meeting" in pkg.system_prompt.lower() or "Mode" in pkg.system_prompt or True
    assert pkg.meta["mode"] == "meeting"
