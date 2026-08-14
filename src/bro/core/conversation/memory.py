from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Deque, Literal

Role = Literal["user", "assistant", "system", "speaker"]


@dataclass(slots=True)
class Message:
    role: Role
    content: str
    ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    meta: dict | None = None


class ConversationMemory:
    """Short-term conversational memory with a fixed window."""

    def __init__(self, max_messages: int = 50) -> None:
        self._messages: Deque[Message] = deque(maxlen=max_messages)

    def add(self, role: Role, content: str, **meta: object) -> Message:
        msg = Message(role=role, content=content, meta=meta or None)
        self._messages.append(msg)
        return msg

    def clear(self) -> None:
        self._messages.clear()

    def history(self) -> list[Message]:
        return list(self._messages)

    def as_chat(self) -> list[dict[str, str]]:
        return [{"role": m.role if m.role != "speaker" else "user", "content": m.content} for m in self._messages]

    def format_text(self, limit: int | None = None) -> str:
        items = list(self._messages)
        if limit is not None:
            items = items[-limit:]
        if not items:
            return "(empty)"
        lines: list[str] = []
        for m in items:
            stamp = m.ts.strftime("%H:%M:%S")
            lines.append(f"[{stamp}] {m.role}: {m.content}")
        return "\n".join(lines)
