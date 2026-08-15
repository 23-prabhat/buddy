from __future__ import annotations

import pytest

from bro.core.commands.handlers import build_registry
from bro.core.commands.parser import parse_command


class FakeSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def write_line(self, text: str, style: str = "info") -> None: ...
    def write_system(self, text: str) -> None: ...

    async def run_screen_read(self, monitor: int | None = None) -> None:
        self.calls.append(("read", {"monitor": monitor}))

    async def run_screen_analyze(self, question: str, monitor: int | None = None) -> None:
        self.calls.append(("analyze", {"question": question, "monitor": monitor}))

    async def run_screen_select(self, question: str = "") -> None:
        self.calls.append(("select", {"question": question}))


@pytest.mark.asyncio
async def test_screen_select_dispatches():
    s = FakeSession()
    reg = build_registry()
    handled = await reg.dispatch('screen select "why is this red"', s)
    assert handled
    assert s.calls == [("select", {"question": "why is this red"})]


@pytest.mark.asyncio
async def test_screen_region_alias_dispatches():
    s = FakeSession()
    reg = build_registry()
    handled = await reg.dispatch("screen region explain it", s)
    assert handled
    assert s.calls == [("select", {"question": "explain it"})]


@pytest.mark.asyncio
async def test_screen_snip_alias_without_question():
    s = FakeSession()
    reg = build_registry()
    handled = await reg.dispatch("screen snip", s)
    assert handled
    assert s.calls == [("select", {"question": ""})]


def test_parse_screen_select():
    cmd = parse_command('screen select "describe this"')
    assert cmd is not None
    assert cmd.name == "screen"
    assert cmd.args[0] == "select"
    assert "describe this" in " ".join(cmd.args)