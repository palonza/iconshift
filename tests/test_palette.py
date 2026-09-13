"""Unit tests for the palette inspector and color extraction."""

from pathlib import Path

from iconshift.palette import PaletteInspector, normalize_hex_color
from iconshift.resolver import ThemeReader


def test_normalize_hex_color():
    assert normalize_hex_color("#fff") == "#FFFFFF"
    assert normalize_hex_color("#123") == "#112233"
    assert normalize_hex_color("#a0a0a0") == "#A0A0A0"
    assert normalize_hex_color("#D0D0D0") == "#D0D0D0"


def test_palette_inspector_with_files(tmp_path: Path):
    svg_dir = tmp_path / "svgs"
    svg_dir.mkdir()

    (svg_dir / "icon1.svg").write_text(
        '<svg><path fill="#A0A0A0"/><path stroke="#A0A0A0"/><rect fill="#404040"/></svg>',
        encoding="utf-8",
    )
    (svg_dir / "icon2.svg").write_text(
        '<svg><circle fill="#A0A0A0"/><circle fill="#FFFFFF"/></svg>',
        encoding="utf-8",
    )

    inspector = PaletteInspector()
    counter = inspector.scan_directory_colors(svg_dir)

    # #A0A0A0 appears 3 times, #404040 appears 1 time, #FFFFFF appears 1 time
    assert counter["#A0A0A0"] == 3
    assert counter["#404040"] == 1
    assert counter["#FFFFFF"] == 1

    # In mock theme
    class FakeThemeReader(ThemeReader):
        def get_theme_paths(self, theme_name: str) -> tuple[Path, ...]:
            return (svg_dir,)

    fake_inspector = PaletteInspector(theme_reader=FakeThemeReader())
    top = fake_inspector.get_top_colors("fake", limit=5)
    assert top[0] == ("#A0A0A0", 3)

    primary, secondary = fake_inspector.detect_palette("fake")
    assert primary == "#A0A0A0"
    assert secondary == "#404040"


def test_palette_inspector_empty_directory(tmp_path: Path):
    inspector = PaletteInspector()
    counter = inspector.scan_directory_colors(tmp_path / "empty")
    assert len(counter) == 0

    class EmptyThemeReader(ThemeReader):
        def get_theme_paths(self, theme_name: str) -> tuple[Path, ...]:
            return ()

    empty_inspector = PaletteInspector(theme_reader=EmptyThemeReader())
    primary, secondary = empty_inspector.detect_palette("unknown")
    assert primary == "#A0A0A0"
    assert secondary == "#404040"
