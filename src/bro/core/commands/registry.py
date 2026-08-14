from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from bro.core.commands.parser import ParsedCommand, parse_command

Handler = Callable[[ParsedCommand, Any], Awaitable[None] | None]


@dataclass(slots=True)
class CommandSpec:
    name: str
    handler: Handler
    help: str
    aliases: tuple[str, ...] = ()


class CommandRegistry:
    def __init__(self) -> None:
        self._commands: dict[str, CommandSpec] = {}

    def register(
        self,
        name: str,
        handler: Handler,
        help: str,
        aliases: tuple[str, ...] = (),
    ) -> None:
        spec = CommandSpec(name=name, handler=handler, help=help, aliases=aliases)
        self._commands[name] = spec
        for alias in aliases:
            self._commands[alias] = spec

    def get(self, name: str) -> CommandSpec | None:
        return self._commands.get(name.lower())

    def list_unique(self) -> list[CommandSpec]:
        seen: set[int] = set()
        out: list[CommandSpec] = []
        for spec in self._commands.values():
            key = id(spec)
            if key in seen:
                continue
            seen.add(key)
            out.append(spec)
        return sorted(out, key=lambda s: s.name)

    async def dispatch(self, line: str, ctx: Any) -> bool:
        """Return True if a command was handled."""
        parsed = parse_command(line)
        if parsed is None:
            return False
        # Bare text without known command → treat as ask
        spec = self.get(parsed.name)
        if spec is None:
            # If first token looks like a command word unknown:
            known_prefixes = {s.name for s in self.list_unique()}
            if parsed.name in known_prefixes:
                return False
            # Natural language → ask
            ask = self.get("ask")
            if ask is None:
                return False
            from bro.core.commands.parser import ParsedCommand as PC

            fake = PC(name="ask", args=[line.strip()], raw=line.strip())
            result = ask.handler(fake, ctx)
            if hasattr(result, "__await__"):
                await result
            return True
        result = spec.handler(parsed, ctx)
        if hasattr(result, "__await__"):
            await result
        return True
