"""SVG Colorizer pipeline implementing Strategy and Filter patterns."""

from __future__ import annotations

from collections import Counter
import math
import re
from typing import Any
import xml.etree.ElementTree as ET
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


def parse_path_bbox(d: str) -> tuple[float, float, float, float] | None:
    """Parses SVG path data commands to compute an approximate bounding box (min_x, min_y, max_x, max_y)."""
    tokens = re.findall(r"([a-zA-Z])|([-+]?(?:[0-9]*\.[0-9]+|[0-9]+)(?:[eE][-+]?[0-9]+)?)", d)
    if not tokens:
        return None

    cur_x, cur_y = 0.0, 0.0
    min_x, max_x = float("inf"), float("-inf")
    min_y, max_y = float("inf"), float("-inf")

    def update_bounds(x: float, y: float) -> None:
        nonlocal min_x, max_x, min_y, max_y
        min_x, max_x = min(min_x, x), max(max_x, x)
        min_y, max_y = min(min_y, y), max(max_y, y)

    items = [(True, c) if c else (False, float(n)) for c, n in tokens]
    idx, total = 0, len(items)
    cmd = ""

    while idx < total:
        is_cmd, val = items[idx]
        if is_cmd:
            cmd = str(val)
            idx += 1

        c_low = cmd.lower()
        is_rel = cmd.islower()
        nums: list[float] = []
        while idx < total and not items[idx][0]:
            nums.append(float(items[idx][1]))
            idx += 1

        if c_low == "z":
            continue
        elif c_low == "h":
            for n in nums:
                cur_x = cur_x + n if is_rel else n
                update_bounds(cur_x, cur_y)
        elif c_low == "v":
            for n in nums:
                cur_y = cur_y + n if is_rel else n
                update_bounds(cur_x, cur_y)
        elif c_low in ("m", "l", "t"):
            for j in range(0, len(nums) - 1, 2):
                nx, ny = nums[j], nums[j + 1]
                cur_x = cur_x + nx if is_rel else nx
                cur_y = cur_y + ny if is_rel else ny
                update_bounds(cur_x, cur_y)
        elif c_low in ("s", "q"):
            for j in range(0, len(nums) - 3, 4):
                nx, ny = nums[j + 2], nums[j + 3]
                cur_x = cur_x + nx if is_rel else nx
                cur_y = cur_y + ny if is_rel else ny
                update_bounds(cur_x, cur_y)
        elif c_low == "c":
            for j in range(0, len(nums) - 5, 6):
                nx, ny = nums[j + 4], nums[j + 5]
                cur_x = cur_x + nx if is_rel else nx
                cur_y = cur_y + ny if is_rel else ny
                update_bounds(cur_x, cur_y)
        elif c_low == "a":
            for j in range(0, len(nums) - 6, 7):
                nx, ny = nums[j + 5], nums[j + 6]
                cur_x = cur_x + nx if is_rel else nx
                cur_y = cur_y + ny if is_rel else ny
                update_bounds(cur_x, cur_y)

    if min_x == float("inf"):
        return None
    return min_x, min_y, max_x, max_y


def extract_gradient_colors(root: ET.Element) -> dict[str, tuple[int, int, int]]:
    """Extracts representative average RGB colors from linear and radial gradients."""
    grads: dict[str, list[tuple[int, int, int]]] = {}
    hrefs: dict[str, str] = {}

    for el in root.iter():
        tag = el.tag.split("}")[-1].lower()
        if tag in ("lineargradient", "radialgradient"):
            gid = el.attrib.get("id")
            if not gid:
                continue
            href = el.attrib.get("{http://www.w3.org/1999/xlink}href") or el.attrib.get("href")
            if href and href.startswith("#"):
                hrefs[gid] = href[1:]

            stops: list[tuple[int, int, int]] = []
            for child in el:
                ctag = child.tag.split("}")[-1].lower()
                if ctag == "stop":
                    c = child.attrib.get("stop-color")
                    st = child.attrib.get("style", "")
                    m_c = re.search(r"stop-color:\s*(#[0-9a-fA-F]{3,6}|rgb\([^\)]+\))", st)
                    if m_c:
                        c = m_c.group(1)
                    if c:
                        rgb = parse_color_to_rgb(c)
                        if rgb:
                            stops.append(rgb)
            if stops:
                grads[gid] = stops

    resolved: dict[str, tuple[int, int, int]] = {}
    for gid in list(grads.keys()) + list(hrefs.keys()):
        cur = gid
        visited: set[str] = set()
        while cur in hrefs and cur not in grads and cur not in visited:
            visited.add(cur)
            cur = hrefs[cur]
        if cur in grads:
            stops = grads[cur]
            avg_r = sum(s[0] for s in stops) // len(stops)
            avg_g = sum(s[1] for s in stops) // len(stops)
            avg_b = sum(s[2] for s in stops) // len(stops)
            resolved[gid] = (avg_r, avg_g, avg_b)

    return resolved


def get_element_geometry(el: ET.Element) -> tuple[float, tuple[float, float, float, float] | None]:
    """Estimates the visual rendered area and bounding box of an SVG element."""
    tag = el.tag.split("}")[-1].lower()
    if tag == "rect":
        x = float(el.attrib.get("x", 0))
        y = float(el.attrib.get("y", 0))
        w = float(el.attrib.get("width", 0))
        h = float(el.attrib.get("height", 0))
        return w * h, (x, y, x + w, y + h)
    elif tag == "circle":
        cx = float(el.attrib.get("cx", 0))
        cy = float(el.attrib.get("cy", 0))
        r = float(el.attrib.get("r", 0))
        return math.pi * r * r, (cx - r, cy - r, cx + r, cy + r)
    elif tag == "ellipse":
        cx = float(el.attrib.get("cx", 0))
        cy = float(el.attrib.get("cy", 0))
        rx = float(el.attrib.get("rx", 0))
        ry = float(el.attrib.get("ry", 0))
        return math.pi * rx * ry, (cx - rx, cy - ry, cx + rx, cy + ry)
    elif tag == "path":
        d = el.attrib.get("d", "")
        bbox = parse_path_bbox(d)
        if not bbox:
            return 0.0, None
        w = max(0.0, bbox[2] - bbox[0])
        h = max(0.0, bbox[3] - bbox[1])
        fill = el.attrib.get("fill", "")
        st = el.attrib.get("style", "")
        m_fill = re.search(r"fill:\s*([^;]+)", st)
        if m_fill:
            fill = m_fill.group(1).strip()
        if fill == "none":
            sw = 1.0
            m_sw = re.search(r"stroke-width:\s*([0-9.]+)", st)
            if m_sw:
                sw = float(m_sw.group(1))
            elif "stroke-width" in el.attrib:
                try:
                    sw = float(el.attrib["stroke-width"])
                except ValueError:
                    pass
            perimeter = 2.0 * (w + h)
            return perimeter * sw, bbox
        return w * h * 0.8, bbox
    return 0.0, None


def analyze_base_and_symbol_colors(content: str) -> tuple[str | None, str | None]:
    """Analyzes the SVG vector shapes to identify the base container and foreground symbols.

    Resolves linear/radial gradients, stroke-only shapes, and bounding box visual areas.
    Identifies the visible base face (using document z-order and area) and foreground symbol.
    Returns (base_color_hex, symbol_color_hex).
    """
    try:
        root = ET.fromstring(content)
    except Exception:
        return None, None

    grads = extract_gradient_colors(root)
    defs_tags = {"defs", "clippath", "mask"}
    ignored: set[ET.Element] = set()
    for el in root.iter():
        if el.tag.split("}")[-1].lower() in defs_tags:
            for c in el.iter():
                ignored.add(c)

    parent_map = {c: p for p in root.iter() for c in p}

    def get_attr(element: ET.Element, name: str) -> str:
        cur: ET.Element | None = element
        while cur is not None:
            v = cur.attrib.get(name)
            if v:
                return v
            st = cur.attrib.get("style", "")
            m = re.search(name + r":\s*([^;]+)", st)
            if m:
                return m.group(1).strip()
            cur = parent_map.get(cur)
        return ""

    shapes: list[dict[str, Any]] = []
    z = 0
    for el in root.iter():
        if el in ignored:
            continue
        tag = el.tag.split("}")[-1].lower()
        if tag not in {"path", "rect", "circle", "ellipse", "polygon", "polyline"}:
            continue

        op = get_attr(el, "opacity") or "1"
        try:
            if float(op) < 0.2:
                continue
        except ValueError:
            pass

        # Color detection: fill takes precedence; if none, check stroke
        fill = get_attr(el, "fill")
        color_rgb: tuple[int, int, int] | None = None

        if fill and fill != "none":
            if fill.startswith("url(#"):
                gid = fill[5:].rstrip(")")
                color_rgb = grads.get(gid)
            else:
                color_rgb = parse_color_to_rgb(fill)
        else:
            stroke = get_attr(el, "stroke")
            if stroke and stroke != "none":
                if stroke.startswith("url(#"):
                    gid = stroke[5:].rstrip(")")
                    color_rgb = grads.get(gid)
                else:
                    color_rgb = parse_color_to_rgb(stroke)

        if color_rgb is not None:
            area, bbox = get_element_geometry(el)
            z += 1
            shapes.append({
                "color": rgb_to_hex(*color_rgb),
                "rgb": color_rgb,
                "area": area,
                "bbox": bbox,
                "z": z,
            })

    if not shapes:
        return None, None

    area_by_color: dict[str, float] = {}
    max_area_by_color: dict[str, float] = {}
    latest_z_by_color: dict[str, int] = {}

    for s in shapes:
        c = s["color"]
        area_by_color[c] = area_by_color.get(c, 0.0) + s["area"]
        max_area_by_color[c] = max(max_area_by_color.get(c, 0.0), s["area"])
        latest_z_by_color[c] = max(latest_z_by_color.get(c, 0), s["z"])

    max_single_area = max(s["area"] for s in shapes)
    large_colors = {
        c for c, max_a in max_area_by_color.items()
        if max_a >= max(1000.0, max_single_area * 0.4)
    }

    if large_colors:
        base_color = max(large_colors, key=lambda col: latest_z_by_color[col])
    else:
        base_color = max(area_by_color.items(), key=lambda item: item[1])[0]

    base_rgb = parse_color_to_rgb(base_color)
    if base_rgb is None:
        return None, None

    # Pick foreground symbol: contrasting color with high visual prominence
    best_sym: str | None = None
    max_contrast_score = -1.0

    for col, total_area in area_by_color.items():
        if col == base_color:
            continue
        # Skip background container layers as symbol candidates
        if col in large_colors and len(large_colors) > 1 and max_area_by_color[col] >= max_single_area * 0.4:
            continue
        c_rgb = parse_color_to_rgb(col)
        if c_rgb is None:
            continue
        dist = color_distance(base_rgb, c_rgb)
        if dist < 40.0:
            continue
        score = dist * math.log10(max(10.0, total_area))
        if score > max_contrast_score:
            max_contrast_score = score
            best_sym = col

    # Fallback if no symbol passed the container filter
    if not best_sym:
        for col, total_area in area_by_color.items():
            if col == base_color:
                continue
            c_rgb = parse_color_to_rgb(col)
            if c_rgb is None:
                continue
            dist = color_distance(base_rgb, c_rgb)
            if dist >= 40.0:
                score = dist * math.log10(max(10.0, total_area))
                if score > max_contrast_score:
                    max_contrast_score = score
                    best_sym = col

    return base_color, best_sym


class AdaptiveDominantStrategy(ColoringStrategy):
    """Adaptive coloring strategy based on the base container and foreground symbols of an SVG.

    Identifies the primary visual container/background (base shape) and inner details/glyphs
    (emblem/symbol), mapping the base shape to the ACYLS primary color and inner details
    to the secondary color.
    """

    def __init__(
        self,
        svg_content: str,
        primary_color: str = "#A0A0A0",
        secondary_color: str = "#404040",
    ) -> None:
        self.primary_color = primary_color.upper()
        self.secondary_color = secondary_color.upper()
        self.base_color: str | None = None
        self.symbol_color: str | None = None

        self._analyze(svg_content)

    def _analyze(self, content: str) -> None:
        base, sym = analyze_base_and_symbol_colors(content)
        if not base:
            # Fallback to frequency counter if XML shapes weren't found
            counter = extract_color_frequencies(content)
            if not counter:
                return
            most_common = counter.most_common()
            base = most_common[0][0]
            base_rgb = hex_to_rgb(base)
            for cand_hex, _ in most_common[1:]:
                cand_rgb = hex_to_rgb(cand_hex)
                if color_distance(base_rgb, cand_rgb) >= 40.0:
                    sym = cand_hex
                    break

        self.base_color = base
        self.symbol_color = sym

    def map_color(self, hex_or_rgb: str) -> str:
        if not self.base_color or not self.symbol_color:
            return self.primary_color

        try:
            rgb = parse_color_to_rgb(hex_or_rgb)
            if rgb is None:
                return self.primary_color

            base_rgb = parse_color_to_rgb(self.base_color)
            sym_rgb = parse_color_to_rgb(self.symbol_color)
            if base_rgb is None or sym_rgb is None:
                return self.primary_color

            d_base = color_distance(rgb, base_rgb)
            d_sym = color_distance(rgb, sym_rgb)

            return self.primary_color if d_base <= d_sym else self.secondary_color
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
