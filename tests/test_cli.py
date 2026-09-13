"""Unit tests for the CLI entry point and argument parsing."""

import pytest

from iconshift.cli import create_parser, get_formatter, main
from iconshift.formatters import JsonFormatter, TableFormatter, TsvFormatter


def test_create_parser():
    parser = create_parser()

    # scan parser
    args_scan = parser.parse_args(["scan", "--theme", "ACYLS", "--missing", "--format", "json"])
    assert args_scan.subcommand == "scan"
    assert args_scan.theme == "ACYLS"
    assert args_scan.missing is True
    assert args_scan.format == "json"

    # generate parser
    args_gen = parser.parse_args([
        "generate",
        "--theme", "ACYLS",
        "--icon", "org.gnome.Snapshot",
        "--color", "#112233",
        "--two-tone",
        "--dry-run",
    ])
    assert args_gen.subcommand == "generate"
    assert args_gen.icon == "org.gnome.Snapshot"
    assert args_gen.color == "#112233"
    assert args_gen.two_tone is True
    assert args_gen.dry_run is True

    # palette parser
    args_pal = parser.parse_args(["palette", "--theme", "ACYLS", "--limit", "10"])
    assert args_pal.subcommand == "palette"
    assert args_pal.limit == 10


def test_get_formatter():
    assert isinstance(get_formatter("table"), TableFormatter)
    assert isinstance(get_formatter("tsv"), TsvFormatter)
    assert isinstance(get_formatter("json"), JsonFormatter)
    # Default fallback
    assert isinstance(get_formatter("unknown"), TableFormatter)


def test_main_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "iconshift" in out


def test_main_subcommand_dispatch(monkeypatch):
    # Test scan dispatch
    monkeypatch.setattr(
        "iconshift.commands.ScanCommand.execute",
        lambda self: 42,
    )
    assert main(["scan"]) == 42

    # Test generate dispatch
    monkeypatch.setattr(
        "iconshift.commands.GenerateCommand.execute",
        lambda self: 43,
    )
    assert main(["generate", "--all"]) == 43

    # Test palette dispatch
    monkeypatch.setattr(
        "iconshift.commands.PaletteCommand.execute",
        lambda self: 44,
    )
    assert main(["palette"]) == 44
