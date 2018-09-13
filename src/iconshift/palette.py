"""Theme palette inspector to extract and count colors from icon SVGs."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Sequence

from iconshift.resolver import ThemeReader

HEX_COLOR_PATTERN = re.compile(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")


def normalize_hex_color(color_str: str) -> str:
    """Normalizes a 3-digit or 6-digit hex color to 6-digit uppercase format."""
    color = color_str.upper()
    if len(color) == 4:  # e.g. #FFF -> #FFFFFF
        return f"#{color[1]*2}{color[2]*2}{color[3]*2}"
    return color


class PaletteInspector:
    """Extracts and counts colors used across a theme's SVG icons."""

    def __init__(self, theme_reader: ThemeReader | None = None) -> None:
        self.theme_reader = theme_reader if theme_reader is not None else ThemeReader()

    def scan_directory_colors(self, directory: Path, max_files: int = 500) -> Counter[str]:
        """Scans SVG files in a directory and aggregates hex color frequencies."""
        counter: Counter[str] = Counter()
        if not directory.is_dir():
            return counter

        scanned = 0
        for svg_file in directory.rglob("*.svg"):
            if not svg_file.is_file():
                continue
            try:
                content = svg_file.read_text(encoding="utf-8", errors="replace")
                matches = HEX_COLOR_PATTERN.findall(content)
                for m in matches:
                    counter[normalize_hex_color(m)] += 1
                scanned += 1
                if scanned >= max_files:
                    break
            except OSError:
                continue

        return counter

    def inspect_theme(self, theme_name: str, max_files: int = 500) -> Counter[str]:
        """Scans all directories of a theme and aggregates color frequencies."""
        theme_paths = self.theme_reader.get_theme_paths(theme_name)
        total_counter: Counter[str] = Counter()

        for theme_dir in theme_paths:
            total_counter.update(self.scan_directory_colors(theme_dir, max_files=max_files))

        return total_counter

    def get_top_colors(
        self,
        theme_name: str,
        limit: int = 20,
    ) -> list[tuple[str, int]]:
        """Returns the most frequent colors for a theme ordered by frequency."""
        counter = self.inspect_theme(theme_name)
        return counter.most_common(limit)

    def detect_palette(
        self,
        theme_name: str,
        default_primary: str = "#A0A0A0",
        default_secondary: str = "#404040",
    ) -> tuple[str, str]:
        """Detects the primary and secondary colors of a theme with fallbacks."""
        top = self.get_top_colors(theme_name, limit=10)
        if not top:
            return default_primary, default_secondary

        # First color is primary
        primary = top[0][0]

        # Secondary is the next most frequent color that is visually distinct
        secondary = default_secondary
        for color, _ in top[1:]:
            if color != primary and color != "#FFFFFF" and color != "#000000":
                secondary = color
                break

        return primary, secondary
