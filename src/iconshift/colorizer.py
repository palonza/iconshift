"""SVG Colorizer pipeline implementing Strategy and Filter patterns."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from pathlib import Path

from iconshift.models import ColorConfig

# Regex patterns for SVG styling and colors
HEX_COLOR_REGEX = re.compile(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
RGB_COLOR_REGEX = re.compile(r"rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)")
RGBA_COLOR_REGEX = re.compile(
    r"rgba\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([0-9.]+)\s*\)"
)


def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    """Converts a hex color string to (r, g, b) tuple."""
    hex_clean = hex_str.lstrip("#")
    if len(hex_clean) == 3:
        hex_clean = "".join([c * 2 for c in hex_clean])
    r = int(hex_clean[0:2], 16)
    g = int(hex_clean[2:4], 16)
    b = int(hex_clean[4:6], 16)
    return r, g, b


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Converts RGB integers to uppercase hex string."""
    return f"#{r:02X}{g:02X}{b:02X}"


def get_luminance(r: int, g: int, b: int) -> float:
    """Calculates perceived luminance based on standard ITU-R BT.601 formula."""
    return 0.299 * r + 0.587 * g + 0.114 * b


class ColoringStrategy(ABC):
    """Abstract coloring strategy for transforming colors in an SVG."""

    @abstractmethod
    def map_color(self, hex_or_rgb: str) -> str:
        """Maps an incoming color string to the desired theme color."""


class MonochromeStrategy(ColoringStrategy):
    """Maps all visible colors to a single primary color."""

    def __init__(self, primary_color: str = "#A0A0A0") -> None:
        self.primary_color = primary_color.upper()

    def map_color(self, hex_or_rgb: str) -> str:
        return self.primary_color


class TwoToneStrategy(ColoringStrategy):
    """Maps light colors to primary and dark colors to secondary for depth."""

    def __init__(
        self,
        primary_color: str = "#A0A0A0",
        secondary_color: str = "#404040",
        threshold: float = 128.0,
    ) -> None:
        self.primary_color = primary_color.upper()
        self.secondary_color = secondary_color.upper()
        self.threshold = threshold

    def map_color(self, hex_or_rgb: str) -> str:
        try:
            if hex_or_rgb.startswith("#"):
                r, g, b = hex_to_rgb(hex_or_rgb)
            elif hex_or_rgb.startswith("rgb"):
                m = RGB_COLOR_REGEX.match(hex_or_rgb)
                if m:
                    r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
                else:
                    return self.primary_color
            else:
                return self.primary_color

            lum = get_luminance(r, g, b)
            return self.primary_color if lum >= self.threshold else self.secondary_color
        except Exception:
            return self.primary_color


class SvgPipeline:
    """Pipeline to process and recolor SVG files safely."""

    def __init__(self, config: ColorConfig | None = None) -> None:
        self.config = config if config is not None else ColorConfig()
        if self.config.two_tone:
            self.strategy: ColoringStrategy = TwoToneStrategy(
                primary_color=self.config.primary,
                secondary_color=self.config.secondary,
            )
        else:
            self.strategy = MonochromeStrategy(primary_color=self.config.primary)

    def recolor_svg_content(
        self,
        content: str,
        strategy: ColoringStrategy | None = None,
    ) -> str:
        """Transforms color values in SVG content while preserving opacity and none."""
        active_strategy = strategy if strategy is not None else self.strategy

        def replace_hex(match: re.Match[str]) -> str:
            val = match.group(0)
            return active_strategy.map_color(val)

        def replace_rgb(match: re.Match[str]) -> str:
            r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
            hex_val = rgb_to_hex(r, g, b)
            return active_strategy.map_color(hex_val)

        # First handle rgb(...)
        processed = RGB_COLOR_REGEX.sub(replace_rgb, content)

        # Then handle hex colors
        processed = HEX_COLOR_REGEX.sub(replace_hex, processed)

        return processed

    def colorize_file(
        self,
        source_path: Path,
        destination_path: Path,
        strategy: ColoringStrategy | None = None,
    ) -> Path:
        """Reads a source SVG, applies coloring, and writes it to destination."""
        if not source_path.is_file():
            raise FileNotFoundError(f"Source icon file not found: {source_path}")

        content = source_path.read_text(encoding="utf-8", errors="replace")
        new_content = self.recolor_svg_content(content, strategy=strategy)

        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_text(new_content, encoding="utf-8")
        return destination_path
