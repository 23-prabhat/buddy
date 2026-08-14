from bro.core.conversation.transcript import RollingTranscript


def test_rolling_transcript():
    t = RollingTranscript(window_seconds=3600)
    t.add("Speaker A", "hello")
    t.add("Speaker B", "why postgres?")
    text = t.format_text()
    assert "Speaker A" in text
    assert "postgres" in text
    assert len(t) == 2
