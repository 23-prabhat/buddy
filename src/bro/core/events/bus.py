from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class Event:
    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


Listener = Callable[[Event], Awaitable[None] | None]


class EventBus:
    def __init__(self) -> None:
        self._listeners: dict[str, list[Listener]] = defaultdict(list)
        self._lock = asyncio.Lock()

    def on(self, name: str, listener: Listener) -> None:
        self._listeners[name].append(listener)

    def off(self, name: str, listener: Listener) -> None:
        if listener in self._listeners[name]:
            self._listeners[name].remove(listener)

    async def emit(self, name: str, **payload: Any) -> None:
        event = Event(name=name, payload=payload)
        listeners = list(self._listeners.get(name, []))
        listeners += list(self._listeners.get("*", []))
        for listener in listeners:
            result = listener(event)
            if asyncio.iscoroutine(result):
                await result
