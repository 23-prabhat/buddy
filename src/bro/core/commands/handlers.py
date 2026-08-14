from __future__ import annotations

from typing import Protocol

from bro.core.commands.parser import ParsedCommand
from bro.core.commands.registry import CommandRegistry
from bro.core.context.engine import AssistantContext


class AppSession(Protocol):
    def write_line(self, text: str, style: str = "info") -> None: ...
    def write_system(self, text: str) -> None: ...
    def clear_output(self) -> None: ...
    def request_exit(self) -> None: ...
    async def run_ask(self, question: str) -> None: ...
    async def run_screen_read(self, monitor: int | None = None) -> None: ...
    async def run_screen_analyze(self, question: str, monitor: int | None = None) -> None: ...
    async def run_listen_start(self) -> None: ...
    async def run_listen_stop(self) -> None: ...
    async def run_meeting_start(self) -> None: ...
    async def run_meeting_stop(self) -> None: ...
    def run_meeting_status(self) -> None: ...
    async def run_rag_add(self, path: str) -> None: ...
    def run_rag_status(self) -> None: ...
    def run_rag_clear(self) -> None: ...
    def get_settings_public(self) -> dict: ...
    def get_history_text(self) -> str: ...
    def get_context_text(self) -> str: ...
    def set_mode(self, mode: str) -> None: ...
    def get_mode(self) -> str: ...
    def get_model_info(self) -> str: ...
    def clear_history(self) -> None: ...
    def stop_tts(self) -> None: ...
    def configure_apikey(self, args: list[str]) -> None: ...
    def configure_provider(self, args: list[str]) -> None: ...
    def list_providers(self) -> None: ...
    def set_model_name(self, model: str) -> None: ...


async def cmd_help(cmd: ParsedCommand, session: AppSession) -> None:
    session.write_system("Available commands:")
    lines = [
        ("help", "Show this help"),
        ("ask <question>", "Ask the AI (streaming)"),
        ("apikey free|own|set <key>|status|clear", "API key mode"),
        ("provider list|<name> [model]", "Select provider (openai/groq/gemini/…)"),
        ("model [name]", "Show or set model id"),
        ("screen read|analyze|clear", "Screen capture / OCR / vision"),
        ("listen [stop]", "One-shot voice question"),
        ("meeting start|stop|status", "Meeting mode + question detect"),
        ("rag add <path>|status|clear", "Personal knowledge base"),
        ("clear", "Clear the terminal view"),
        ("history", "Show conversation history"),
        ("context", "Show current context summary"),
        ("settings", "Show configuration (secrets redacted)"),
        ("mode [name]", "Get or set mode"),
        ("stop", "Stop TTS playback"),
        ("exit / quit", "Leave the application"),
    ]
    for name, desc in lines:
        session.write_line(f"  {name:<40} {desc}", "muted")


async def cmd_ask(cmd: ParsedCommand, session: AppSession) -> None:
    question = " ".join(cmd.args).strip()
    if not question:
        session.write_line('[ERROR] Usage: ask "your question"', "error")
        return
    await session.run_ask(question)


async def cmd_apikey(cmd: ParsedCommand, session: AppSession) -> None:
    session.configure_apikey(cmd.args)


async def cmd_provider(cmd: ParsedCommand, session: AppSession) -> None:
    if not cmd.args or cmd.args[0].lower() in ("list", "ls", "help"):
        session.list_providers()
        return
    session.configure_provider(cmd.args)


async def cmd_screen(cmd: ParsedCommand, session: AppSession) -> None:
    if not cmd.args:
        session.write_line(
            '[ERROR] Usage: screen read | screen analyze ["question"] | screen clear',
            "error",
        )
        return
    sub = cmd.args[0].lower()
    rest = cmd.args[1:]
    if sub == "read":
        monitor = int(rest[0]) if rest and rest[0].isdigit() else None
        await session.run_screen_read(monitor=monitor)
        return
    if sub in ("analyze", "analyse"):
        await session.run_screen_analyze(question=" ".join(rest).strip())
        return
    if sub == "clear":
        if hasattr(session, "screen_text"):
            session.screen_text = ""  # type: ignore[attr-defined]
            session.screen_description = ""  # type: ignore[attr-defined]
            session.last_screen_summary = ""  # type: ignore[attr-defined]
        session.write_system("[SCREEN] Context cleared.")
        return
    session.write_line("[ERROR] Unknown screen subcommand. Use: read | analyze | clear", "error")


async def cmd_listen(cmd: ParsedCommand, session: AppSession) -> None:
    if cmd.args and cmd.args[0].lower() in ("stop", "off", "end"):
        await session.run_listen_stop()
        return
    await session.run_listen_start()


async def cmd_meeting(cmd: ParsedCommand, session: AppSession) -> None:
    if not cmd.args:
        session.run_meeting_status()
        return
    sub = cmd.args[0].lower()
    if sub in ("start", "on"):
        await session.run_meeting_start()
    elif sub in ("stop", "off", "end"):
        await session.run_meeting_stop()
    elif sub == "status":
        session.run_meeting_status()
    elif sub == "inject" and len(cmd.args) > 1:
        text = " ".join(cmd.args[1:]).strip()
        if hasattr(session, "inject_meeting_text"):
            await session.inject_meeting_text(text)  # type: ignore[attr-defined]
        else:
            session.write_line("[ERROR] inject not available", "error")
    else:
        session.write_line(
            '[ERROR] Usage: meeting start | stop | status | inject "text"',
            "error",
        )


async def cmd_rag(cmd: ParsedCommand, session: AppSession) -> None:
    if not cmd.args:
        session.run_rag_status()
        return
    sub = cmd.args[0].lower()
    if sub == "add":
        path = " ".join(cmd.args[1:]).strip()
        if not path:
            session.write_line("[ERROR] Usage: rag add <path>", "error")
            return
        await session.run_rag_add(path)
    elif sub == "status":
        session.run_rag_status()
    elif sub == "clear":
        session.run_rag_clear()
    else:
        session.write_line("[ERROR] Usage: rag add <path> | status | clear", "error")


async def cmd_clear(cmd: ParsedCommand, session: AppSession) -> None:
    session.clear_output()
    session.write_system("Cleared.")


async def cmd_history(cmd: ParsedCommand, session: AppSession) -> None:
    session.write_system("[HISTORY]")
    session.write_line(session.get_history_text(), "muted")


async def cmd_context(cmd: ParsedCommand, session: AppSession) -> None:
    session.write_system("[CONTEXT]")
    session.write_line(session.get_context_text(), "muted")


async def cmd_settings(cmd: ParsedCommand, session: AppSession) -> None:
    session.write_system("[SETTINGS]")
    for key, value in session.get_settings_public().items():
        session.write_line(f"  {key} = {value}", "muted")


async def cmd_model(cmd: ParsedCommand, session: AppSession) -> None:
    if not cmd.args:
        session.write_system(session.get_model_info())
        return
    session.set_model_name(" ".join(cmd.args).strip())


async def cmd_mode(cmd: ParsedCommand, session: AppSession) -> None:
    if not cmd.args:
        session.write_system(f"[MODE] {session.get_mode()}")
        return
    mode = cmd.args[0].strip().lower()
    allowed = {"general", "meeting", "screen", "meeting+screen", "coding", "study"}
    if mode not in allowed:
        session.write_line(
            f"[ERROR] Unknown mode. Choose: {', '.join(sorted(allowed))}",
            "error",
        )
        return
    session.set_mode(mode)
    session.write_system(f"[MODE] {mode}")


async def cmd_stop(cmd: ParsedCommand, session: AppSession) -> None:
    session.stop_tts()
    session.write_system("[TTS] Stopped.")


async def cmd_exit(cmd: ParsedCommand, session: AppSession) -> None:
    session.write_system("Goodbye.")
    session.request_exit()


def build_registry() -> CommandRegistry:
    reg = CommandRegistry()
    reg.register("help", cmd_help, "Show help", aliases=("?",))
    reg.register("ask", cmd_ask, "Ask the AI")
    reg.register("apikey", cmd_apikey, "API key mode", aliases=("key", "api-key"))
    reg.register("provider", cmd_provider, "Select AI provider", aliases=("providers",))
    reg.register("screen", cmd_screen, "Screen capture / analyze")
    reg.register("listen", cmd_listen, "Voice listen")
    reg.register("meeting", cmd_meeting, "Meeting mode")
    reg.register("rag", cmd_rag, "Personal knowledge")
    reg.register("clear", cmd_clear, "Clear terminal")
    reg.register("history", cmd_history, "Conversation history")
    reg.register("context", cmd_context, "Show context")
    reg.register("settings", cmd_settings, "Show settings")
    reg.register("model", cmd_model, "Show/set model")
    reg.register("mode", cmd_mode, "Get/set mode")
    reg.register("stop", cmd_stop, "Stop TTS")
    reg.register("exit", cmd_exit, "Exit", aliases=("quit", "q"))
    reg.register("answer", cmd_ask, "Alias-style answer trigger")
    return reg


def make_assistant_context(
    question: str,
    history: list[dict[str, str]],
    mode: str,
    meeting_transcript: str = "",
    screen_text: str = "",
    screen_description: str = "",
    detected_speaker: str | None = None,
    rag_context: str = "",
) -> AssistantContext:
    return AssistantContext(
        user_question=question,
        conversation_history=history,
        mode=mode,
        meeting_transcript=meeting_transcript,
        current_screen_text=screen_text,
        screen_description=screen_description,
        detected_speaker=detected_speaker,
        rag_context=rag_context,
    )
