"""Unit tests for the SVG Colorizer and strategies."""

from pathlib import Path
import pytest

from iconshift.colorizer import (
    MonochromeStrategy,
    SvgPipeline,
    TwoToneStrategy,
    get_luminance,
    hex_to_rgb,
    rgb_to_hex,
)
from iconshift.models import ColorConfig


def test_color_utilities():
    assert hex_to_rgb("#FFFFFF") == (255, 255, 255)
    assert hex_to_rgb("#000000") == (0, 0, 0)
    assert hex_to_rgb("#FFF") == (255, 255, 255)
    assert hex_to_rgb("#A0A0A0") == (160, 160, 160)

    assert rgb_to_hex(255, 255, 255) == "#FFFFFF"
    assert rgb_to_hex(0, 0, 0) == "#000000"
    assert rgb_to_hex(160, 160, 160) == "#A0A0A0"

    assert get_luminance(255, 255, 255) == 255.0
    assert get_luminance(0, 0, 0) == 0.0


def test_monochrome_strategy():
    strat = MonochromeStrategy(primary_color="#D0D0D0")
    assert strat.map_color("#123456") == "#D0D0D0"
    assert strat.map_color("#FFFFFF") == "#D0D0D0"
    assert strat.map_color("rgb(10, 20, 30)") == "#D0D0D0"


def test_two_tone_strategy():
    strat = TwoToneStrategy(primary_color="#A0A0A0", secondary_color="#404040")
    # White (light) -> primary
    assert strat.map_color("#FFFFFF") == "#A0A0A0"
    # Black (dark) -> secondary
    assert strat.map_color("#000000") == "#404040"
    # RGB light
    assert strat.map_color("rgb(220, 220, 220)") == "#A0A0A0"
    # RGB dark
    assert strat.map_color("rgb(20, 20, 20)") == "#404040"


def test_svg_pipeline_recolor_content():
    svg_input = (
        '<svg viewBox="0 0 100 100">\n'
        '  <rect fill="#FF5500" stroke="#003366" opacity="0.8"/>\n'
        '  <circle fill="none" stroke="rgb(50, 100, 150)"/>\n'
        '  <path fill="transparent"/>\n'
        '</svg>'
    )

    pipeline = SvgPipeline(ColorConfig(primary="#A0A0A0"))
    result = pipeline.recolor_svg_content(svg_input)

    # Replaced colors
    assert 'fill="#A0A0A0"' in result
    assert 'stroke="#A0A0A0"' in result

    # Preserved none, transparent, opacity
    assert 'fill="none"' in result
    assert 'fill="transparent"' in result
    assert 'opacity="0.8"' in result
    assert "#FF5500" not in result
    assert "#003366" not in result


def test_svg_pipeline_colorize_file(tmp_path: Path):
    src = tmp_path / "source.svg"
    dst = tmp_path / "nested/out.svg"

    src.write_text('<svg fill="#123456"/>', encoding="utf-8")

    pipeline = SvgPipeline(ColorConfig(primary="#A0A0A0"))
    out_path = pipeline.colorize_file(src, dst)

    assert out_path.is_file()
    content = out_path.read_text(encoding="utf-8")
    assert 'fill="#A0A0A0"' in content

    # Non-existent source
    with pytest.raises(FileNotFoundError):
        pipeline.colorize_file(tmp_path / "missing.svg", dst)
