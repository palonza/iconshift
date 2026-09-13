"""Data Transfer Objects and Models for IconShift."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ResolutionSource(str, Enum):
    """Enumeration of where an icon was resolved from."""
    TARGET_THEME = "target_theme"
    INHERITED_THEME = "inherited_theme"
    PIXMAPS = "pixmaps"
    OPT = "opt"
    ABSOLUTE = "absolute"
    NOT_FOUND = "not_found"

    def label(self) -> str:
        """Human-readable label."""
        labels = {
            self.TARGET_THEME: "TARGET",
            self.INHERITED_THEME: "INHERITED",
            self.PIXMAPS: "PIXMAPS",
            self.OPT: "OPT",
            self.ABSOLUTE: "ABSOLUTE",
            self.NOT_FOUND: "NOT_FOUND",
        }
        return labels.get(self, self.value)


@dataclass(frozen=True)
class DesktopEntry:
    """Represents a parsed Freedesktop .desktop application file."""
    desktop_path: Path
    name: str
    icon_name: str
    no_display: bool = False
    terminal: bool = False

    @property
    def has_icon(self) -> bool:
        """Whether the desktop file specifies an icon."""
        return bool(self.icon_name and self.icon_name.strip())

    @property
    def is_absolute_icon(self) -> bool:
        """Whether the icon points directly to an absolute path."""
        return self.icon_name.startswith("/")


@dataclass(frozen=True)
class ResolvedIcon:
    """Result of attempting to resolve an icon across the theme hierarchy."""
    icon_name: str
    source: ResolutionSource
    source_theme: str | None = None
    resolved_path: Path | None = None
    format: str | None = None

    @property
    def is_resolved(self) -> bool:
        """Whether the icon was located anywhere on the system."""
        return self.source != ResolutionSource.NOT_FOUND and self.resolved_path is not None

    @property
    def is_in_target_theme(self) -> bool:
        """Whether the icon is already present in the target theme."""
        return self.source == ResolutionSource.TARGET_THEME

    @property
    def is_missing_in_target(self) -> bool:
        """Whether the icon is missing in target theme, but resolved elsewhere."""
        return self.is_resolved and not self.is_in_target_theme


@dataclass(frozen=True)
class ThemeMetadata:
    """Metadata parsed from an icon theme's index.theme."""
    name: str
    theme_dirs: tuple[Path, ...]
    inherits: tuple[str, ...] = ()
    comment: str | None = None


@dataclass(frozen=True)
class ColorConfig:
    """Color configuration for icon colorization."""
    primary: str = "#A0A0A0"
    secondary: str = "#404040"
    two_tone: bool = False
    mode: str = "adaptive"  # "adaptive", "two_tone", "monochrome"
    exceptions: dict[str, str] = field(default_factory=dict)

    @property
    def effective_mode(self) -> str:
        """Determines the effective coloring mode considering backwards compatibility."""
        if self.two_tone:
            return "two_tone"
        return self.mode

