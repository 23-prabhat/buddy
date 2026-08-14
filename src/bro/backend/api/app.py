from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from bro.ai.providers.factory import create_ai_provider
from bro.audio.stt.factory import create_stt_provider
from bro.core.configuration import get_settings
from bro.core.context.engine import AssistantContext, ContextEngine
from bro.tts.providers.factory import create_tts_provider

app = FastAPI(title="bro-assistant-api", version="0.3.0")


class AskRequest(BaseModel):
    question: str
    meeting_transcript: str = ""
    screen_text: str = ""
    screen_description: str = ""
    rag_context: str = ""
    mode: str = "general"
    history: list[dict[str, str]] = Field(default_factory=list)


class AskResponse(BaseModel):
    answer: str
    provider: str
    model: str


class VisionRequest(BaseModel):
    prompt: str = "Describe this screen."
    # base64 png without data-url prefix optional later; for now text-only path
    image_b64: str = ""


class TranscribeResponse(BaseModel):
    text: str
    provider: str


class TTSRequest(BaseModel):
    text: str


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "phase": "3-9", "app": "bro"}


@app.get("/api/models")
async def models() -> dict[str, Any]:
    s = get_settings()
    return {
        "ai_provider": s.ai_provider,
        "ai_model": s.ai_model,
        "stt_provider": s.stt_provider,
        "tts_provider": s.tts_provider,
    }


@app.get("/api/settings")
async def settings_public() -> dict[str, Any]:
    return get_settings().public_dict()


@app.post("/api/ask", response_model=AskResponse)
async def ask(body: AskRequest) -> AskResponse:
    s = get_settings()
    try:
        provider = create_ai_provider(s)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    engine = ContextEngine(s)
    pkg = engine.build(
        AssistantContext(
            user_question=body.question,
            meeting_transcript=body.meeting_transcript,
            current_screen_text=body.screen_text,
            screen_description=body.screen_description,
            rag_context=body.rag_context,
            conversation_history=body.history,
            mode=body.mode,
        )
    )
    answer = await provider.answer(pkg)
    return AskResponse(answer=answer, provider=provider.name, model=s.ai_model)


@app.post("/api/tts")
async def tts(body: TTSRequest) -> dict[str, str]:
    s = get_settings()
    provider = create_tts_provider(s)
    await provider.speak(body.text)
    return {"status": "ok", "provider": provider.name}


@app.post("/api/transcribe")
async def transcribe_info() -> dict[str, str]:
    """Placeholder metadata — binary upload can be added later."""
    s = get_settings()
    stt = create_stt_provider(s)
    return {
        "status": "ready",
        "provider": stt.name,
        "hint": "Desktop app streams mic→STT; API binary upload planned.",
    }
