from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from bro.ai.providers.base import AIProvider
from bro.ai.providers.factory import create_ai_provider
from bro.core.commands.handlers import make_assistant_context
from bro.core.commands.registry import CommandRegistry
from bro.core.configuration.settings import Settings, get_settings
from bro.core.context.engine import ContextEngine
from bro.core.conversation.memory import ConversationMemory
from bro.core.conversation.transcript import RollingTranscript
from bro.core.events.bus import EventBus
from bro.osplat.screen_capture import get_platform_service
from bro.rag.retrieval.store import VectorStore
from bro.vision.ocr.tesseract import TesseractOcrProvider
from bro.vision.pipeline import ScreenPipeline


class TerminalSession:
    """Bridge between command handlers and the UI widgets."""

    def __init__(
        self,
        registry: CommandRegistry,
        settings: Settings | None = None,
        on_line: Callable[[str, str], None] | None = None,
        on_clear: Callable[[], None] | None = None,
        on_exit: Callable[[], None] | None = None,
        on_status: Callable[[], None] | None = None,
        on_stream_start: Callable[[], None] | None = None,
        on_stream_chunk: Callable[[str], None] | None = None,
        on_stream_end: Callable[[], None] | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.registry = registry
        self.memory = ConversationMemory()
        self.events = EventBus()
        self.context_engine = ContextEngine(self.settings)
        self.provider: AIProvider = create_ai_provider(self.settings)
        self.mode = self.settings.mode
        self.busy = False
        self.meeting_on = False
        self.screen_active = False
        self.screen_text = ""
        self.screen_description = ""
        self.last_screen_summary = ""
        self.last_response = ""
        self.transcript = RollingTranscript(window_seconds=self.settings.meeting_context_seconds)
        self.rag = VectorStore()
        self._pending_screenshot: Any = None  # Screenshot set by UI for region select
        self._pending_region: tuple[int, int, int, int] | None = None

        self._platform = get_platform_service()
        self._ocr = TesseractOcrProvider(lang=self.settings.ocr_lang)
        self._screen = ScreenPipeline(
            platform=self._platform,
            ocr=self._ocr,
            ai=self.provider,
            force_vision=self.settings.screen_force_vision,
        )

        if self.settings.rag_path:
            try:
                n = self.rag.ingest_path(self.settings.rag_path)
                if n:
                    pass
            except Exception:  # noqa: BLE001
                pass

        self._on_line = on_line or (lambda _t, _s: None)
        self._on_clear = on_clear or (lambda: None)
        self._on_exit = on_exit or (lambda: None)
        self._on_status = on_status or (lambda: None)
        self._on_stream_start = on_stream_start or (lambda: None)
        self._on_stream_chunk = on_stream_chunk or (lambda _c: None)
        self._on_stream_end = on_stream_end or (lambda: None)

    # --- AppSession protocol ---

    def write_line(self, text: str, style: str = "info") -> None:
        self._on_line(text, style)

    def write_system(self, text: str) -> None:
        self._on_line(text, "system")

    def clear_output(self) -> None:
        self._on_clear()

    def request_exit(self) -> None:
        asyncio.create_task(self._shutdown())
        self._on_exit()

    async def _shutdown(self) -> None:
        self.meeting_on = False
        await self.run_meeting_stop()

    def get_settings_public(self) -> dict[str, Any]:
        return self.settings.public_dict()

    def get_history_text(self) -> str:
        return self.memory.format_text()

    def get_context_text(self) -> str:
        lines = [
            f"mode={self.mode}",
            f"provider={self.provider.name}",
            f"model={self.settings.ai_model}",
            f"history_messages={len(self.memory.history())}",
            f"meeting_lines={len(self.transcript)}",
            f"screen_text_chars={len(self.screen_text)}",
            f"screen_description_chars={len(self.screen_description)}",
            f"rag_chunks={len(self.rag)}",
            f"last_screen={self.last_screen_summary or '(none)'}",
        ]
        if self.screen_text:
            preview = self.screen_text[:300].replace("\n", " ")
            lines.append(f"screen_text_preview={preview}")
        mt = self.transcript.format_text()
        if mt:
            lines.append("--- meeting transcript ---")
            lines.append(mt[-1500:])
        return "\n".join(lines)

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self._on_status()

    def get_mode(self) -> str:
        return self.mode

    def get_model_info(self) -> str:
        from bro.ai.providers.factory import describe_ai_config

        info = describe_ai_config(self.settings)
        return (
            f"[MODEL] mode={info['key_mode']} provider={info['provider']} "
            f"model={info['model']} base={info['base_url']} "
            f"key={info['api_key_preview']}"
        )

    def clear_history(self) -> None:
        self.memory.clear()

    def _persist_and_reload(self, updates: dict[str, str]) -> None:
        from bro.core.configuration.envfile import upsert_env_values
        from bro.core.configuration.settings import reload_settings

        upsert_env_values(updates)
        self.settings = reload_settings()
        try:
            self.reload_provider()
        except Exception as exc:  # noqa: BLE001
            self.write_line(f"[WARN] Provider reload: {exc}", "warn")

    def list_providers(self) -> None:
        from bro.ai.providers.catalog import list_providers_help

        self.write_system("[PROVIDERS] OpenAI-compatible endpoints")
        for line in list_providers_help():
            self.write_line(f"  {line}", "muted")
        self.write_line(
            'Usage: provider <name> [model]   e.g. provider groq llama-3.3-70b-versatile',
            "muted",
        )
        self.write_line(
            "Then: apikey set <YOUR_KEY>   (switches to own key mode)",
            "muted",
        )
        self.write_line("Or:  apikey free              (built-in free Groq)", "muted")

    def configure_apikey(self, args: list[str]) -> None:
        if not args:
            self.write_system(self.get_model_info())
            self.write_line(
                "Usage: apikey free | own | set <key> | status | clear | mock",
                "muted",
            )
            return
        sub = args[0].lower()
        if sub in ("status", "show"):
            self.write_system(self.get_model_info())
            return
        if sub in ("free", "builtin", "default"):
            self._persist_and_reload({"AI_KEY_MODE": "free"})
            self.write_system("[APIKEY] Using free built-in Groq API")
            self.write_system(self.get_model_info())
            return
        if sub in ("own", "user", "custom"):
            if not (self.settings.ai_api_key or "").strip():
                self.write_line(
                    "[WARN] No personal key saved yet. Use: apikey set <your-key>",
                    "warn",
                )
            self._persist_and_reload({"AI_KEY_MODE": "own"})
            self.write_system("[APIKEY] Using your own API key")
            self.write_system(self.get_model_info())
            return
        if sub in ("mock", "offline", "none"):
            self._persist_and_reload({"AI_KEY_MODE": "mock"})
            self.write_system("[APIKEY] Mock / offline mode")
            self.write_system(self.get_model_info())
            return
        if sub in ("clear", "unset", "remove"):
            self._persist_and_reload({"AI_API_KEY": "", "AI_KEY_MODE": "free"})
            self.write_system("[APIKEY] Personal key cleared; switched to free mode")
            self.write_system(self.get_model_info())
            return
        if sub == "set":
            key = " ".join(args[1:]).strip().strip('"').strip("'")
            if not key:
                self.write_line("[ERROR] Usage: apikey set <your-api-key>", "error")
                return
            updates = {"AI_API_KEY": key, "AI_KEY_MODE": "own"}
            # Heuristic: groq keys often start with gsk_
            if key.startswith("gsk_") and not (self.settings.ai_provider or "").strip():
                updates["AI_PROVIDER"] = "groq"
            self._persist_and_reload(updates)
            self.write_system("[APIKEY] Saved your key (own mode)")
            self.write_system(self.get_model_info())
            return
        # bare key paste: apikey gsk_xxx
        if len(args) == 1 and len(args[0]) > 20:
            self.configure_apikey(["set", args[0]])
            return
        self.write_line(
            "[ERROR] Usage: apikey free | own | set <key> | status | clear | mock",
            "error",
        )

    def configure_provider(self, args: list[str]) -> None:
        from bro.ai.providers.catalog import PROVIDERS, resolve_provider_id

        if not args:
            self.list_providers()
            return
        name = args[0].strip().lower()
        pid = resolve_provider_id(name)
        if pid is None:
            self.write_line(f"[ERROR] Unknown provider: {name}", "error")
            self.list_providers()
            return
        preset = PROVIDERS[pid]
        model = " ".join(args[1:]).strip() if len(args) > 1 else preset.default_model
        updates = {
            "AI_PROVIDER": pid,
            "AI_MODEL": model,
            "AI_BASE_URL": preset.base_url,
            "AI_KEY_MODE": "own" if pid != "mock" else "mock",
        }
        if pid == "mock":
            updates["AI_KEY_MODE"] = "mock"
        self._persist_and_reload(updates)
        self.write_system(f"[PROVIDER] {preset.label} · model={model}")
        if pid != "mock" and not (self.settings.ai_api_key or "").strip():
            self.write_line(
                "[INFO] Set your key: apikey set <YOUR_KEY>   (or apikey free)",
                "muted",
            )
        self.write_system(self.get_model_info())

    def set_model_name(self, model: str) -> None:
        model = model.strip()
        if not model:
            self.write_line("[ERROR] Usage: model <model-id>", "error")
            return
        mode = (self.settings.ai_key_mode or "free").lower()
        if mode in ("free", "builtin", "default"):
            self._persist_and_reload({"FREE_AI_MODEL": model, "AI_MODEL": model})
        else:
            self._persist_and_reload({"AI_MODEL": model})
        self.write_system(f"[MODEL] Set to {model}")
        self.write_system(self.get_model_info())

    def _rag_for(self, question: str) -> str:
        if not self.settings.rag_enabled or not len(self.rag):
            return ""
        return self.rag.format_context(question)

    def _effective_mode(self) -> str:
        if self.mode == "meeting+screen":
            return "meeting+screen"
        if self.meeting_on and (self.screen_text or self.screen_description):
            return "meeting+screen"
        if self.meeting_on:
            return "meeting"
        return self.mode

    async def run_ask(self, question: str, speaker: str | None = None) -> None:
        if self.busy:
            self.write_line("[WARN] Already generating an answer.", "warn")
            return
        self.busy = True
        self._on_status()
        try:
            await self._answer(question, speaker=speaker)
        finally:
            self.busy = False
            self._on_status()

    async def _answer(self, question: str, speaker: str | None = None) -> None:
        self.memory.add("user", question)
        mode = self._effective_mode()
        # Auto-include fresh screen in meeting+screen when configured
        if mode in ("meeting+screen", "screen") and self.settings.screen_capture_enabled:
            if mode == "meeting+screen" and not (self.screen_text or self.screen_description):
                try:
                    result = await self._screen.understand(
                        monitor=self.settings.screen_monitor,
                        question=None,
                        use_vision=False,
                    )
                    self.screen_text = result.ocr.text
                    self.screen_description = result.description
                    self.last_screen_summary = result.source_summary
                    self.write_system(f"[SCREEN] auto {result.source_summary}")
                except Exception as exc:  # noqa: BLE001
                    self.write_line(f"[WARN] Auto screen capture failed: {exc}", "warn")

        ctx = make_assistant_context(
            question=question,
            history=self.memory.as_chat()[:-1],
            mode=mode,
            meeting_transcript=self.transcript.format_text(),
            screen_text=self.screen_text,
            screen_description=self.screen_description,
            detected_speaker=speaker,
            rag_context=self._rag_for(question),
        )
        package = self.context_engine.build(ctx)
        self.write_system("[AI] Generating...")
        self._on_stream_start()
        parts: list[str] = []
        try:
            async for chunk in self.provider.answer_stream(package):
                parts.append(chunk)
                self._on_stream_chunk(chunk)
        except Exception as exc:  # noqa: BLE001
            self.write_line(f"[ERROR] AI provider failed: {exc}", "error")
            self.write_line(
                "[INFO] Check AI_API_KEY / AI_PROVIDER in .env or use AI_PROVIDER=mock",
                "muted",
            )
            return
        finally:
            self._on_stream_end()
        answer = "".join(parts).strip()
        if answer:
            self.last_response = answer
            self.memory.add("assistant", answer)
            await self.events.emit("answer", text=answer)
        else:
            self.write_line("[WARN] Empty response from provider.", "warn")

    async def run_screen_read(
        self,
        monitor: int | None = None,
        region: tuple[int, int, int, int] | None = None,
    ) -> None:
        if not self.settings.screen_capture_enabled:
            self.write_line(
                "[ERROR] Screen capture disabled. Set SCREEN_CAPTURE_ENABLED=true in .env",
                "error",
            )
            return
        if self.busy:
            self.write_line("[WARN] Already busy.", "warn")
            return
        mon = self.settings.screen_monitor if monitor is None else monitor
        self.busy = True
        self.screen_active = True
        self._on_status()
        try:
            self.write_system("[SCREEN] Capturing...")
            result = await self._screen.understand(
                monitor=mon, question=None, use_vision=False, region=region
            )
            self.screen_text = result.ocr.text
            self.screen_description = result.description
            self.last_screen_summary = result.source_summary
            self.write_system(f"[SCREEN] {result.source_summary}")
            if result.ocr.error:
                self.write_line(f"[OCR] {result.ocr.error}", "warn")
            if result.ocr.text:
                preview = (
                    result.ocr.text
                    if len(result.ocr.text) <= 1500
                    else result.ocr.text[:1500] + "\n…[truncated]"
                )
                self.write_system("[OCR]")
                self.write_line(preview, "muted")
            else:
                self.write_line("[OCR] (no text extracted)", "muted")
            self.write_line(
                '[INFO] Screen context stored. Use: ask "…" or screen analyze "…"',
                "muted",
            )
        except Exception as exc:  # noqa: BLE001
            self.write_line(f"[ERROR] Screen capture failed: {exc}", "error")
        finally:
            self.busy = False
            self.screen_active = False
            self._on_status()

    async def run_screen_analyze(
        self,
        question: str,
        monitor: int | None = None,
        region: tuple[int, int, int, int] | None = None,
    ) -> None:
        if not self.settings.screen_capture_enabled:
            self.write_line(
                "[ERROR] Screen capture disabled. Set SCREEN_CAPTURE_ENABLED=true in .env",
                "error",
            )
            return
        if self.busy:
            self.write_line("[WARN] Already busy.", "warn")
            return
        mon = self.settings.screen_monitor if monitor is None else monitor
        self.busy = True
        self.screen_active = True
        self._on_status()
        try:
            self.write_system("[SCREEN] Capturing...")
            screenshot = self._pending_screenshot
            reg = region or self._pending_region
            result = await self._screen.understand(
                monitor=mon,
                question=question or "Explain what is on this screen.",
                use_vision=True,
                region=reg,
                screenshot=screenshot,
            )
            self.screen_text = result.ocr.text
            self.screen_description = result.description
            self.last_screen_summary = result.source_summary
            self.write_system(f"[SCREEN] {result.source_summary}")
            if result.ocr.error:
                self.write_line(f"[OCR] {result.ocr.error}", "warn")
            if result.ocr.text:
                preview = (
                    result.ocr.text
                    if len(result.ocr.text) <= 800
                    else result.ocr.text[:800] + "\n…[truncated]"
                )
                self.write_system("[OCR]")
                self.write_line(preview, "muted")
            if result.used_vision and result.description:
                self.write_system("[VISION]")
                self.write_line(result.description, "muted")
            q = question.strip() or "Explain what is on this screen."
            self.write_system("[AI] Analyzing screen + question...")
            prev_mode = self.mode
            if self.mode == "general":
                self.mode = "screen"
            await self._answer(q)
            self.mode = prev_mode
        except Exception as exc:  # noqa: BLE001
            self.write_line(f"[ERROR] Screen analyze failed: {exc}", "error")
        finally:
            self._pending_screenshot = None
            self._pending_region = None
            self.busy = False
            self.screen_active = False
            self._on_status()

    async def run_screen_select(self, question: str = "") -> None:
        """Analyze a user-selected screen region.

        The UI layer captures a full screenshot, shows a region selector, then
        stashes the result in ``_pending_screenshot`` / ``_pending_region`` and
        dispatches here. Falls back to a prompt if the UI didn't preselect.
        """
        if not self.settings.screen_capture_enabled:
            self.write_line(
                "[ERROR] Screen capture disabled. Set SCREEN_CAPTURE_ENABLED=true in .env",
                "error",
            )
            return
        if self._pending_screenshot is None and self._pending_region is None:
            self.write_line(
                "[HINT] Region selection needs the desktop UI. "
                'Use: screen select "question"  (drag a rectangle on screen)',
                "muted",
            )
            return
        await self.run_screen_analyze(question)

    async def run_meeting_start(self) -> None:
        if self.meeting_on:
            self.write_line("[WARN] Meeting already running.", "warn")
            return
        if self.mode == "general":
            self.mode = "meeting"
        self.meeting_on = True
        self.write_system("[MEETING] Started (text-only mode)")
        self.write_system(
            "[INFO] Audio transcription removed. Paste lines with: "
            'meeting inject "what was said"'
        )
        self.write_system(f"[CONTEXT] Rolling window: {self.settings.meeting_context_seconds}s")
        self._on_status()

    async def run_meeting_stop(self) -> None:
        self.meeting_on = False
        self.write_system("[MEETING] Stopped")
        self._on_status()

    def run_meeting_status(self) -> None:
        state = "running" if self.meeting_on else "stopped"
        self.write_system(f"[MEETING] {state} · lines={len(self.transcript)}")
        mt = self.transcript.format_text()
        if mt:
            self.write_line(mt[-1200:], "muted")
        else:
            self.write_line("  (no transcript yet — use: meeting inject \"text\")", "muted")

    async def inject_meeting_text(self, text: str) -> None:
        """Push a transcript line as if spoken, then run question detection."""
        self.transcript.add("Speaker A", text, source="inject")
        self.write_line(f'Speaker A: "{text}"', "info")
        from bro.ai.reasoning.question_detect import QuestionDetector

        det = QuestionDetector().detect(text, speaker="Speaker A")
        if det.is_question and det.directed_at_user:
            self.write_system(f"[QUESTION] Detected (conf={det.confidence:.2f}) · {det.reason}")
            if self.settings.meeting_auto_answer and not self.busy:
                self.busy = True
                self._on_status()
                try:
                    await self._answer(det.normalized, speaker="Speaker A")
                finally:
                    self.busy = False
                    self._on_status()

    async def run_rag_add(self, path: str) -> None:
        try:
            n = await asyncio.to_thread(self.rag.ingest_path, path)
            self.write_system(f"[RAG] Ingested {n} chunks from {path}")
        except Exception as exc:  # noqa: BLE001
            self.write_line(f"[ERROR] RAG ingest failed: {exc}", "error")

    def run_rag_status(self) -> None:
        self.write_system(f"[RAG] chunks={len(self.rag)} enabled={self.settings.rag_enabled}")

    def run_rag_clear(self) -> None:
        self.rag.clear()
        self.write_system("[RAG] Cleared.")

    async def handle_line(self, line: str) -> None:
        text = line.strip()
        if not text:
            return
        await self.registry.dispatch(text, self)

    def status_flags(self) -> dict[str, str]:
        ai = "BUSY" if self.busy else "READY"
        if self.meeting_on:
            ai = "LISTENING" if not self.busy else "BUSY"
        screen = "ON" if self.screen_active else (
            "READY" if self.settings.screen_capture_enabled else "OFF"
        )
        return {
            "MEETING": "ON" if self.meeting_on else "OFF",
            "SCREEN": screen,
            "AI": ai,
            "MODE": self.mode,
        }

    def reload_provider(self) -> None:
        self.provider = create_ai_provider(self.settings)
        self._screen.ai = self.provider
