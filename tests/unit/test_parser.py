from bro.core.commands.parser import parse_command


def test_parse_simple():
    cmd = parse_command("help")
    assert cmd is not None
    assert cmd.name == "help"
    assert cmd.args == []


def test_parse_ask_quoted():
    cmd = parse_command('ask "why postgres?"')
    assert cmd is not None
    assert cmd.name == "ask"
    assert cmd.args == ["why postgres?"]


def test_parse_dollar_prefix():
    cmd = parse_command("$ meeting start")
    assert cmd is not None
    assert cmd.name == "meeting"
    assert cmd.args == ["start"]


def test_parse_empty():
    assert parse_command("   ") is None
