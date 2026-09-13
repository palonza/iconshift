"""Unit tests for Command implementations."""

import io
from pathlib import Path

from iconshift.colorizer import SvgPipeline
from iconshift.commands import (
    ColorizeIconCommand,
    GenerateCommand,
    PaletteCommand,
    ScanCommand,
)
from iconshift.formatters import TableFormatter
from iconshift.palette import PaletteInspector
from iconshift.resolver import IconResolver
from iconshift.scanner import DesktopScanner


def test_colorize_icon_command_dry_run(tmp_path: Path):
    src = tmp_path / "src.svg"
    src.write_text('<svg fill="#000"/>', encoding="utf-8")
    dst = tmp_path / "dst.svg"

    cmd = ColorizeIconCommand(
        source_path=src,
        destination_path=dst,
        pipeline=SvgPipeline(),
        dry_run=True,
    )
    assert cmd.execute() is True
    assert not dst.exists()


def test_colorize_icon_command_success(tmp_path: Path):
    src = tmp_path / "src.svg"
    src.write_text('<svg fill="#000"/>', encoding="utf-8")
    dst = tmp_path / "dst.svg"

    cmd = ColorizeIconCommand(
        source_path=src,
        destination_path=dst,
        pipeline=SvgPipeline(),
        dry_run=False,
    )
    assert cmd.execute() is True
    assert dst.is_file()


def test_colorize_icon_command_invalid_file(tmp_path: Path):
    src = tmp_path / "missing.svg"
    dst = tmp_path / "dst.svg"

    cmd = ColorizeIconCommand(
        source_path=src,
        destination_path=dst,
        pipeline=SvgPipeline(),
    )
    assert cmd.execute() is False

    # Non-SVG
    png = tmp_path / "src.png"
    png.write_text("PNG", encoding="utf-8")
    cmd_png = ColorizeIconCommand(
        source_path=png,
        destination_path=dst,
        pipeline=SvgPipeline(),
    )
    assert cmd_png.execute() is False


def test_scan_command_execution(mock_env, capsys):
    resolver = IconResolver(
        target_theme="ACYLS",
        icon_dirs=mock_env["icon_dirs"],
        pixmap_dirs=mock_env["pixmap_dirs"],
        opt_dirs=mock_env["opt_dirs"],
    )
    scanner = DesktopScanner(
        applications_dirs=mock_env["apps_dirs"],
        resolver=resolver,
    )

    cmd = ScanCommand(
        theme="ACYLS",
        missing_only=True,
        formatter=TableFormatter(),
        scanner=scanner,
    )
    assert cmd.execute() == 0
    out = capsys.readouterr().out
    assert "APPLICATION" in out
    assert "Camera" in out


def test_generate_command_single_icon(mock_env, tmp_path: Path):
    resolver = IconResolver(
        target_theme="ACYLS",
        icon_dirs=mock_env["icon_dirs"],
        pixmap_dirs=mock_env["pixmap_dirs"],
        opt_dirs=mock_env["opt_dirs"],
    )
    scanner = DesktopScanner(
        applications_dirs=mock_env["apps_dirs"],
        resolver=resolver,
    )
    out_dir = tmp_path / "icons_out"

    cmd = GenerateCommand(
        theme="ACYLS",
        icon_name="org.gnome.Snapshot",
        output_dir=out_dir,
        resolver=resolver,
        scanner=scanner,
    )
    assert cmd.execute() == 0
    assert (out_dir / "org.gnome.Snapshot.svg").is_file()


def test_generate_command_all_missing(mock_env, tmp_path: Path):
    resolver = IconResolver(
        target_theme="ACYLS",
        icon_dirs=mock_env["icon_dirs"],
        pixmap_dirs=mock_env["pixmap_dirs"],
        opt_dirs=mock_env["opt_dirs"],
    )
    scanner = DesktopScanner(
        applications_dirs=mock_env["apps_dirs"],
        resolver=resolver,
    )
    out_dir = tmp_path / "icons_out"

    cmd = GenerateCommand(
        theme="ACYLS",
        all_missing=True,
        output_dir=out_dir,
        resolver=resolver,
        scanner=scanner,
    )
    assert cmd.execute() == 0
    # SVG missing icons should be generated
    assert (out_dir / "org.gnome.Snapshot.svg").is_file()
    assert (out_dir / "vlc.svg").is_file()


def test_generate_command_from_stdin(mock_env, tmp_path: Path, monkeypatch):
    resolver = IconResolver(
        target_theme="ACYLS",
        icon_dirs=mock_env["icon_dirs"],
        pixmap_dirs=mock_env["pixmap_dirs"],
        opt_dirs=mock_env["opt_dirs"],
    )
    scanner = DesktopScanner(
        applications_dirs=mock_env["apps_dirs"],
        resolver=resolver,
    )
    out_dir = tmp_path / "icons_out"

    monkeypatch.setattr("sys.stdin", io.StringIO("vlc\norg.gnome.Snapshot\n"))

    cmd = GenerateCommand(
        theme="ACYLS",
        from_stdin=True,
        output_dir=out_dir,
        resolver=resolver,
        scanner=scanner,
    )
    assert cmd.execute() == 0
    assert (out_dir / "vlc.svg").is_file()
    assert (out_dir / "org.gnome.Snapshot.svg").is_file()


def test_palette_command(capsys):
    class FakeInspector(PaletteInspector):
        def get_top_colors(self, theme_name: str, limit: int = 20):
            return [("#A0A0A0", 50), ("#404040", 20)]

        def detect_palette(self, theme_name: str, **kwargs):
            return "#A0A0A0", "#404040"

    cmd = PaletteCommand(theme="ACYLS", inspector=FakeInspector())
    assert cmd.execute() == 0
    out = capsys.readouterr().out
    assert "#A0A0A0" in out
    assert "#404040" in out
