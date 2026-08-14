from __future__ import annotations

import shlex
from dataclasses import dataclass, field


@dataclass(slots=True)
class ParsedCommand:
    name: str
    args: list[str] = field(default_factory=list)
    raw: str = ""


def parse_command(line: str) -> ParsedCommand | None:
    text = line.strip()
    if not text:
        return None
    # Allow leading $ like a shell prompt paste
    if text.startswith("$"):
        text = text[1:].lstrip()
    if not text:
        return None
    try:
        parts = shlex.split(text)
    except ValueError:
        parts = text.split()
    if not parts:
        return None
    name = parts[0].lower()
    return ParsedCommand(name=name, args=parts[1:], raw=line.strip())
