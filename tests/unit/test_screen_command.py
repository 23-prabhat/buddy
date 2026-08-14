from bro.core.commands.parser import parse_command
from bro.core.commands.handlers import build_registry


def test_parse_screen_read():
    cmd = parse_command("screen read")
    assert cmd is not None
    assert cmd.name == "screen"
    assert cmd.args == ["read"]


def test_parse_screen_analyze():
    cmd = parse_command('screen analyze "why segfault"')
    assert cmd is not None
    assert cmd.name == "screen"
    assert cmd.args[0] == "analyze"
    assert "segfault" in " ".join(cmd.args)


def test_registry_has_screen():
    reg = build_registry()
    assert reg.get("screen") is not None
