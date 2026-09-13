"""SVG Colorizer pipeline implementing Strategy and Filter patterns."""

from __future__ import annotations

from collections import Counter
import re
from abc import ABC, abstractmethod
from pathlib import Path

from iconshift.models import ColorConfig

# Regex patterns for SVG styling and colors
HEX_COLOR_REGEX = re.compile(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
RGB_COLOR_REGEX = re.compile(
    r"rgb\s*\(\s*([0-9.]+%?)\s*,\s*([0-9.]+%?)\s*,\s*([0-9.]+%?)\s*\)"
)
RGBA_COLOR_REGEX = re.compile(
    r"rgba\s*\(\s*([0-9.]+%?)\s*,\s*([0-9.]+%?)\s*,\s*([0-9.]+%?)\s*,\s*([0-9.]+)\s*\)"
)


def parse_rgb_component(val: str) -> int:
    """Parses an RGB channel value (integer, float, or percentage) to integer 0-255."""
    clean = val.strip()
    if clean.endswith("%"):
        return max(0, min(255, round(float(clean[:-1]) * 2.55)))
    return max(0, min(255, round(float(clean))))


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


def color_distance(rgb1: tuple[int, int, int], rgb2: tuple[int, int, int]) -> float:
    """Calculates Euclidean distance in RGB color space."""
    return ((rgb1[0] - rgb2[0]) ** 2 + (rgb1[1] - rgb2[1]) ** 2 + (rgb1[2] - rgb2[2]) ** 2) ** 0.5


def parse_color_to_rgb(color_str: str) -> tuple[int, int, int] | None:
    """Extracts (r, g, b) integers from hex, rgb(), or rgba() color strings."""
    clean = color_str.strip()
    if clean.startswith("#"):
        try:
            return hex_to_rgb(clean)
        except Exception:
            return None
    elif clean.startswith("rgba"):
        m = RGBA_COLOR_REGEX.match(clean)
        if m:
            return (
                parse_rgb_component(m.group(1)),
                parse_rgb_component(m.group(2)),
                parse_rgb_component(m.group(3)),
            )
    elif clean.startswith("rgb"):
        m = RGB_COLOR_REGEX.match(clean)
        if m:
            return (
                parse_rgb_component(m.group(1)),
                parse_rgb_component(m.group(2)),
                parse_rgb_component(m.group(3)),
            )
    return None


def extract_color_frequencies(content: str) -> Counter[str]:
    """Extracts all visible colors from SVG content and counts occurrences in hex format."""
    counter: Counter[str] = Counter()

    # 1. rgba(...) - exclude transparent/invisible stops
    for match in RGBA_COLOR_REGEX.finditer(content):
        try:
            alpha = float(match.group(4).strip())
            if alpha < 0.05:
                continue
            r = parse_rgb_component(match.group(1))
            g = parse_rgb_component(match.group(2))
            b = parse_rgb_component(match.group(3))
            counter[rgb_to_hex(r, g, b)] += 1
        except Exception:
            continue

    # 2. rgb(...) - exclude rgba to avoid double matching
    content_no_rgba = RGBA_COLOR_REGEX.sub("", content)
    for match in RGB_COLOR_REGEX.finditer(content_no_rgba):
        try:
            r = parse_rgb_component(match.group(1))
            g = parse_rgb_component(match.group(2))
            b = parse_rgb_component(match.group(3))
            counter[rgb_to_hex(r, g, b)] += 1
        except Exception:
            continue

    # 3. hex colors
    for match in HEX_COLOR_REGEX.finditer(content):
        hex_val = match.group(0).upper()
        if len(hex_val) == 4:
            hex_val = f"#{hex_val[1]*2}{hex_val[2]*2}{hex_val[3]*2}"
        counter[hex_val] += 1

    return counter



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
                    r = parse_rgb_component(m.group(1))
                    g = parse_rgb_component(m.group(2))
                    b = parse_rgb_component(m.group(3))
                else:
                    return self.primary_color
            else:
                return self.primary_color

            lum = get_luminance(r, g, b)
            return self.primary_color if lum >= self.threshold else self.secondary_color
        except Exception:
            return self.primary_color


class AdaptiveDominantStrategy(ColoringStrategy):
    """Adaptive coloring strategy based on the dominant and secondary colors of an SVG.

    Identifies the primary visual container/background (dominant color) and inner details/glyphs
    (secondary color), preserving contrast polarity and mapping to the ACYLS theme palette.
    """

    def __init__(
        self,
        svg_content: str,
        primary_color: str = "#A0A0A0",
        secondary_color: str = "#404040",
    ) -> None:
        self.primary_color = primary_color.upper()
        self.secondary_color = secondary_color.upper()
        self.dominant_color: str | None = None
        self.secondary_color_src: str | None = None
        self.split_by_luminance: bool = True
        self.luminance_midpoint: float = 128.0
        self.target_light: str = self.primary_color
        self.target_dark: str = self.secondary_color
        self.dominant_maps_to: str = self.primary_color
        self.secondary_maps_to: str = self.secondary_color

        self._analyze(svg_content)

    def _analyze(self, content: str) -> None:
        counter = extract_color_frequencies(content)
        if not counter:
            return

        most_common = counter.most_common()
        dom_hex, _ = most_common[0]
        self.dominant_color = dom_hex
        dom_rgb = hex_to_rgb(dom_hex)
        dom_lum = get_luminance(*dom_rgb)

        # Look for the most frequent secondary color with sufficient perceptual difference
        sec_hex: str | None = None
        sec_rgb: tuple[int, int, int] | None = None
        sec_lum: float | None = None

        for cand_hex, _ in most_common[1:]:
            cand_rgb = hex_to_rgb(cand_hex)
            cand_lum = get_luminance(*cand_rgb)
            lum_diff = abs(cand_lum - dom_lum)
            dist = color_distance(dom_rgb, cand_rgb)
            if lum_diff >= 25.0 or dist >= 45.0:
                sec_hex = cand_hex
                sec_rgb = cand_rgb
                sec_lum = cand_lum
                break

        # Theme target light/dark assignment
        p_rgb = hex_to_rgb(self.primary_color)
        s_rgb = hex_to_rgb(self.secondary_color)
        p_lum = get_luminance(*p_rgb)
        s_lum = get_luminance(*s_rgb)

        self.target_light = self.primary_color if p_lum >= s_lum else self.secondary_color
        self.target_dark = self.secondary_color if s_lum <= p_lum else self.primary_color

        if sec_hex is None or sec_rgb is None or sec_lum is None:
            # Flat single-tone icon: everything maps to theme primary
            self.dominant_maps_to = self.primary_color
            self.secondary_maps_to = self.primary_color
            self.split_by_luminance = False
            return

        self.secondary_color_src = sec_hex

        lum_diff = abs(dom_lum - sec_lum)
        if lum_diff >= 20.0:
            self.split_by_luminance = True
            self.luminance_midpoint = (dom_lum + sec_lum) / 2.0
            if dom_lum < sec_lum:
                # Dominant is darker than secondary (e.g. Console dark card, light prompt)
                self.dominant_maps_to = self.target_dark
                self.secondary_maps_to = self.target_light
            else:
                # Dominant is lighter than secondary (e.g. Characters light sheet, dark letters)
                self.dominant_maps_to = self.target_light
                self.secondary_maps_to = self.target_dark
        else:
            # Different hue with close luminance: split by Euclidean distance
            self.split_by_luminance = False
            self.dominant_maps_to = self.target_light
            self.secondary_maps_to = self.target_dark

    def map_color(self, hex_or_rgb: str) -> str:
        if self.dominant_color is None or self.secondary_color_src is None:
            return self.primary_color

        try:
            rgb = parse_color_to_rgb(hex_or_rgb)
            if rgb is None:
                return self.primary_color

            if self.split_by_luminance:
                lum = get_luminance(*rgb)
                return self.target_light if lum >= self.luminance_midpoint else self.target_dark
            else:
                dom_rgb = hex_to_rgb(self.dominant_color)
                sec_rgb = hex_to_rgb(self.secondary_color_src)
                d_dom = color_distance(rgb, dom_rgb)
                d_sec = color_distance(rgb, sec_rgb)
                return self.dominant_maps_to if d_dom <= d_sec else self.secondary_maps_to
        except Exception:
            return self.primary_color


class SvgPipeline:
    """Pipeline to process and recolor SVG files safely."""

    def __init__(self, config: ColorConfig | None = None) -> None:
        self.config = config if config is not None else ColorConfig()
        mode = self.config.effective_mode
        if mode == "monochrome":
            self.default_strategy: ColoringStrategy | None = MonochromeStrategy(
                primary_color=self.config.primary
            )
        elif mode == "two_tone":
            self.default_strategy = TwoToneStrategy(
                primary_color=self.config.primary,
                secondary_color=self.config.secondary,
            )
        else:
            # "adaptive" (default): dynamic strategy instantiated per SVG content
            self.default_strategy = None

    def recolor_svg_content(
        self,
        content: str,
        strategy: ColoringStrategy | None = None,
    ) -> str:
        """Transforms color values in SVG content while preserving opacity and none."""
        if strategy is not None:
            active_strategy = strategy
        elif self.default_strategy is not None:
            active_strategy = self.default_strategy
        else:
            active_strategy = AdaptiveDominantStrategy(
                svg_content=content,
                primary_color=self.config.primary,
                secondary_color=self.config.secondary,
            )


        def replace_hex(match: re.Match[str]) -> str:
            val = match.group(0)
            return active_strategy.map_color(val)

        def replace_rgb(match: re.Match[str]) -> str:
            r = parse_rgb_component(match.group(1))
            g = parse_rgb_component(match.group(2))
            b = parse_rgb_component(match.group(3))
            hex_val = rgb_to_hex(r, g, b)
            return active_strategy.map_color(hex_val)

        def replace_rgba(match: re.Match[str]) -> str:
            r = parse_rgb_component(match.group(1))
            g = parse_rgb_component(match.group(2))
            b = parse_rgb_component(match.group(3))
            hex_val = rgb_to_hex(r, g, b)
            alpha = match.group(4)
            mapped_hex = active_strategy.map_color(hex_val)
            mr, mg, mb = hex_to_rgb(mapped_hex)
            return f"rgba({mr}, {mg}, {mb}, {alpha})"

        # First handle rgba(...)
        processed = RGBA_COLOR_REGEX.sub(replace_rgba, content)

        # Then handle rgb(...)
        processed = RGB_COLOR_REGEX.sub(replace_rgb, processed)

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
