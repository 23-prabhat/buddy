from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from bro.core.configuration.settings import Settings


@dataclass
class AssistantContext:
    meeting_transcript: str = ""
    current_screen_text: str = ""
    screen_description: str = ""
    user_question: str = ""
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    detected_speaker: str | None = None
    application_name: str | None = None
    mode: str = "general"
    rag_context: str = ""


@dataclass
class ContextPackage:
    system_prompt: str
    user_content: str
    messages: list[dict[str, str]]
    meta: dict[str, Any] = field(default_factory=dict)


STYLE_INSTRUCTIONS = {
    "concise": "Answer in 1-3 short sentences. Prefer spoken brevity.",
    "balanced": (
        "Give a direct short answer first, then a brief explanation. "
        "Optimize for speaking during a meeting."
    ),
    "detailed": "Provide a clear answer with supporting detail, still structured and scannable.",
    "technical": "Be precise and technical; include tradeoffs when relevant. Stay focused.",
}


class ContextEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def build(self, ctx: AssistantContext) -> ContextPackage:
        style = STYLE_INSTRUCTIONS.get(self.settings.response_style, STYLE_INSTRUCTIONS["balanced"])
        parts: list[str] = [
            "You are a real-time AI copilot for meetings and on-screen work.",
            "Be accurate, practical, and easy to speak aloud.",
            style,
            f"Current mode: {ctx.mode}.",
        ]
        if ctx.application_name:
            parts.append(f"Active application: {ctx.application_name}.")
        if ctx.detected_speaker:
            parts.append(f"Detected speaker: {ctx.detected_speaker}.")

        # Mode-aware source priority hints
        mode = (ctx.mode or "general").lower()
        if mode == "meeting":
            parts.append("Prioritize meeting transcript and the current question.")
        elif mode == "screen":
            parts.append("Prioritize on-screen content and the current question.")
        elif mode in ("meeting+screen", "meeting_screen"):
            parts.append("Combine meeting transcript and screen when both are relevant.")
        elif mode == "coding":
            parts.append("Focus on code, errors, and technical correctness.")
        elif mode == "study":
            parts.append("Teach clearly; define terms briefly when helpful.")

        system_prompt = "\n".join(parts)

        blocks: list[str] = []
        if ctx.user_question.strip():
            blocks.append(f"## User question\n{ctx.user_question.strip()}")
        if ctx.meeting_transcript.strip() and mode in (
            "meeting",
            "meeting+screen",
            "meeting_screen",
            "general",
            "coding",
            "study",
        ):
            transcript = ctx.meeting_transcript.strip()
            if len(transcript) > 4000:
                transcript = transcript[-4000:]
            blocks.append(f"## Meeting transcript (recent)\n{transcript}")
        if ctx.current_screen_text.strip() and mode in (
            "screen",
            "meeting+screen",
            "meeting_screen",
            "general",
            "coding",
            "study",
        ):
            screen = ctx.current_screen_text.strip()
            if len(screen) > 6000:
                screen = screen[:6000] + "\n…[truncated]"
            blocks.append(f"## Screen text\n{screen}")
        if ctx.screen_description.strip() and mode in (
            "screen",
            "meeting+screen",
            "meeting_screen",
            "general",
            "coding",
            "study",
        ):
            blocks.append(f"## Screen description\n{ctx.screen_description.strip()}")
        if ctx.rag_context.strip():
            rag = ctx.rag_context.strip()
            if len(rag) > 3500:
                rag = rag[:3500] + "\n…[truncated]"
            blocks.append(f"## Personal knowledge (retrieved)\n{rag}")

        user_content = "\n\n".join(blocks) if blocks else "No user question provided."
        history = [m for m in ctx.conversation_history[-20:] if m.get("content")]

        return ContextPackage(
            system_prompt=system_prompt,
            user_content=user_content,
            messages=history,
            meta={"mode": ctx.mode, "style": self.settings.response_style},
        )
