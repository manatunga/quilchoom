"""
Unit tests for Quilchoom's terminal presentation helpers.
"""

from rich.console import Console

from quilchoom.ui import terminal


def test_header(monkeypatch, capsys):
    test_console = Console(color_system=None)
    monkeypatch.setattr(terminal, "console", test_console)

    terminal.header("INIT")

    output = capsys.readouterr().out

    assert output == "\nQUILCHOOM / INIT\n\n"


def test_info(monkeypatch, capsys):
    test_console = Console(color_system=None)
    monkeypatch.setattr(terminal, "console", test_console)

    terminal.info("Development activity is already current.")

    output = capsys.readouterr().out

    assert output == "• Development activity is already current.\n"


def test_success(monkeypatch, capsys):
    test_console = Console(color_system=None)
    monkeypatch.setattr(terminal, "console", test_console)

    terminal.success("Quilchoom initialized.")

    output = capsys.readouterr().out

    assert output == "✓ Quilchoom initialized.\n"


def test_warning(monkeypatch, capsys):
    test_console = Console(color_system=None)
    monkeypatch.setattr(terminal, "console", test_console)

    terminal.warning("4 evidence records await distillation.")

    output = capsys.readouterr().out

    assert output == "! 4 evidence records await distillation.\n"


def test_error(monkeypatch, capsys):
    test_console = Console(color_system=None)
    monkeypatch.setattr(terminal, "console", test_console)

    terminal.error("Something went wrong.")

    output = capsys.readouterr().out

    assert output == "× Something went wrong.\n"


def test_next_action(monkeypatch, capsys):
    test_console = Console(color_system=None)
    monkeypatch.setattr(terminal, "console", test_console)

    terminal.next_action("Run `quilchoom init`.")

    output = capsys.readouterr().out

    assert output == "→ Run `quilchoom init`.\n"


def test_field(monkeypatch, capsys):
    test_console = Console(color_system=None)
    monkeypatch.setattr(terminal, "console", test_console)

    terminal.field("Project", "quilchoom")

    output = capsys.readouterr().out

    assert output == "• Project: quilchoom\n"


def test_error_block_with_action(monkeypatch, capsys):
    test_console = Console(color_system=None)
    monkeypatch.setattr(terminal, "console", test_console)

    terminal.error_block(
        title="Not initialized.",
        explanation="Quilchoom local state is missing.",
        action="Run `quilchoom init`.",
    )

    output = capsys.readouterr().out

    assert output == (
        "× Not initialized.\n"
        "\n"
        "  Quilchoom local state is missing.\n"
        "\n"
        "  → Run `quilchoom init`.\n"
    )


def test_error_block_without_action(monkeypatch, capsys):
    test_console = Console(color_system=None)
    monkeypatch.setattr(terminal, "console", test_console)

    terminal.error_block(
        title="Operation failed.",
        explanation="The operation could not be completed.",
    )

    output = capsys.readouterr().out

    assert output == (
        "× Operation failed.\n\n  The operation could not be completed.\n"
    )


def test_progress_is_silent_for_non_terminal_console(monkeypatch, capsys):
    test_console = Console(color_system=None, force_terminal=False)
    monkeypatch.setattr(terminal, "console", test_console)

    with terminal.Progress("Working..."):
        pass

    output = capsys.readouterr().out

    assert output == ""
