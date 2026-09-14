"""Icon resolution engine using Chain of Responsibility and Freedesktop Icon Theme spec."""

from __future__ import annotations

import configparser
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Sequence

from iconshift.models import ResolutionSource, ResolvedIcon, ThemeMetadata

SUPPORTED_EXTENSIONS = (".svg", ".png", ".xpm")

# Standard Freedesktop / GNOME RDNN application aliases
STANDARD_ICON_ALIASES: dict[str, tuple[str, ...]] = {
    # System Settings & Preferences
    "org.gnome.Settings": ("gnome-settings", "preferences-system", "gnome-control-center"),
    "gnome-control-center": ("gnome-settings", "preferences-system", "org.gnome.Settings"),
    "preferences-system": ("gnome-settings", "org.gnome.Settings"),

    # Calculator
    "org.gnome.Calculator": ("gnome-calculator", "accessories-calculator"),
    "accessories-calculator": ("gnome-calculator", "org.gnome.Calculator"),
    "gnome-calculator": ("accessories-calculator", "org.gnome.Calculator"),

    # Terminal / Console
    "org.gnome.Console": ("utilities-terminal", "gnome-terminal", "terminal"),
    "org.gnome.Terminal": ("utilities-terminal", "gnome-terminal", "terminal"),
    "utilities-terminal": ("gnome-terminal", "terminal", "org.gnome.Console"),

    # Camera / Snapshot
    "org.gnome.Snapshot": ("camera-photo", "camera", "accessories-camera"),
    "camera-photo": ("camera", "org.gnome.Snapshot"),

    # Characters
    "org.gnome.Characters": ("gnome-characters", "accessories-character-map", "gucharmap", "character-set"),
    "accessories-character-map": ("gnome-characters", "gucharmap", "org.gnome.Characters"),

    # Contacts
    "org.gnome.Contacts": ("address-book-new", "contact-new", "gnome-contacts"),

    # Files / File Manager
    "org.gnome.Nautilus": ("system-file-manager", "nautilus"),

    # Text Editor
    "org.gnome.TextEditor": ("accessories-text-editor", "text-editor", "gedit"),
    "org.gnome.gedit": ("accessories-text-editor", "text-editor", "gedit"),

    # System Monitor
    "org.gnome.SystemMonitor": ("utilities-system-monitor", "gnome-system-monitor"),

    # Software / App Store
    "org.gnome.Software": ("software-store", "system-software-install", "gnome-software"),

    # Clocks
    "org.gnome.clocks": ("clocks", "preferences-system-time"),
    "org.gnome.Clocks": ("clocks", "preferences-system-time"),

    # Calendar
    "org.gnome.Calendar": ("calendar", "x-office-calendar"),

    # Music / Audio
    "org.gnome.Music": ("media-audio-player", "gnome-music"),

    # Weather
    "org.gnome.Weather": ("weather", "gnome-weather"),

    # Maps
    "org.gnome.Maps": ("maps", "gnome-maps"),

    # Document Viewer / Evince
    "org.gnome.Evince": ("x-office-document", "document-viewer", "evince"),
    "org.gnome.Papers": ("x-office-document", "document-viewer", "evince"),
}


def get_icon_name_candidates(icon_name: str) -> tuple[str, ...]:
    """Returns candidate icon names including standard Freedesktop/RDNN aliases."""
    candidates = [icon_name]
    aliases = STANDARD_ICON_ALIASES.get(icon_name, ())
    for a in aliases:
        if a not in candidates:
            candidates.append(a)

    base = icon_name
    for ext in SUPPORTED_EXTENSIONS:
        if base.endswith(ext):
            base = base[: -len(ext)]
            break
    if base != icon_name:
        if base not in candidates:
            candidates.append(base)
        for a in STANDARD_ICON_ALIASES.get(base, ()):
            if a not in candidates:
                candidates.append(a)

    return tuple(candidates)


def get_default_icon_dirs() -> tuple[Path, ...]:
    """Default directories where icon themes are installed in Linux."""
    home = Path.home()
    return (
        home / ".local/share/icons",
        Path("/usr/local/share/icons"),
        Path("/usr/share/icons"),
    )


def get_default_pixmap_dirs() -> tuple[Path, ...]:
    """Default directories where application pixmaps are stored."""
    home = Path.home()
    return (
        home / ".local/share/pixmaps",
        Path("/usr/share/pixmaps"),
    )


def get_default_opt_dirs() -> tuple[Path, ...]:
    """Default directories where third-party packages (like /opt) are installed."""
    return (Path("/opt"),)


class ThemeReader:
    """Reads icon theme configuration and resolves transitive theme inheritance."""

    def __init__(self, icon_dirs: Sequence[Path] | None = None) -> None:
        self.icon_dirs = tuple(icon_dirs) if icon_dirs is not None else get_default_icon_dirs()

    def get_theme_paths(self, theme_name: str) -> tuple[Path, ...]:
        """Returns existing directory paths for a given theme name."""
        found: list[Path] = []
        for base_dir in self.icon_dirs:
            theme_path = base_dir / theme_name
            if theme_path.is_dir():
                found.append(theme_path)
        return tuple(found)

    def read_metadata(self, theme_name: str) -> ThemeMetadata:
        """Reads index.theme from the highest-priority directory of the theme."""
        theme_paths = self.get_theme_paths(theme_name)
        inherits_list: list[str] = []
        comment: str | None = None

        for theme_dir in theme_paths:
            index_file = theme_dir / "index.theme"
            if index_file.is_file():
                config = configparser.ConfigParser(interpolation=None)
                try:
                    config.read(index_file, encoding="utf-8")
                    if "Icon Theme" in config:
                        section = config["Icon Theme"]
                        raw_inherits = section.get("Inherits", "")
                        if raw_inherits:
                            inherits_list = [
                                t.strip()
                                for t in raw_inherits.split(",")
                                if t.strip()
                            ]
                        comment = section.get("Comment", None)
                        break
                except Exception:
                    # Continue trying next theme directory if index is malformed
                    pass

        return ThemeMetadata(
            name=theme_name,
            theme_dirs=theme_paths,
            inherits=tuple(inherits_list),
            comment=comment,
        )

    def resolve_inheritance_chain(self, theme_name: str) -> tuple[str, ...]:
        """Resolves the complete, ordered chain of inherited themes without duplicates."""
        chain: list[str] = []
        visited: set[str] = {theme_name.lower()}
        queue: list[str] = [theme_name]

        while queue:
            current = queue.pop(0)
            meta = self.read_metadata(current)
            for inherited in meta.inherits:
                low = inherited.lower()
                if low not in visited:
                    visited.add(low)
                    chain.append(inherited)
                    queue.append(inherited)

        # Freedesktop specification: 'hicolor' is the ultimate fallback
        if "hicolor" not in visited:
            chain.append("hicolor")

        return tuple(chain)


def find_icon_in_directory(directory: Path, icon_name: str) -> Path | None:
    """Finds an icon file within a directory tree, preferring .svg over .png over .xpm."""
    # Strip extension if passed directly in icon_name
    base_name = icon_name
    for ext in SUPPORTED_EXTENSIONS:
        if base_name.endswith(ext):
            base_name = base_name[: -len(ext)]
            break

    # First check direct file matches in directory
    for ext in SUPPORTED_EXTENSIONS:
        candidate = directory / f"{base_name}{ext}"
        if candidate.is_file():
            return candidate

    # Search subdirectories (e.g. scalable/apps, 48x48/apps)
    # Priority: search for svg first across tree, then png, then xpm
    for ext in SUPPORTED_EXTENSIONS:
        pattern = f"{base_name}{ext}"
        for match in directory.rglob(pattern):
            if match.is_file():
                return match

    return None


class ResolutionLink(ABC):
    """Abstract link in the Chain of Responsibility for icon resolution."""

    def __init__(self, next_link: ResolutionLink | None = None) -> None:
        self.next_link = next_link

    def resolve(self, icon_name: str) -> ResolvedIcon:
        """Attempts to resolve the icon, delegating to the next link if not found."""
        result = self.try_resolve(icon_name)
        if result is not None:
            return result
        if self.next_link is not None:
            return self.next_link.resolve(icon_name)
        return ResolvedIcon(
            icon_name=icon_name,
            source=ResolutionSource.NOT_FOUND,
        )

    @abstractmethod
    def try_resolve(self, icon_name: str) -> ResolvedIcon | None:
        """Tries to resolve the icon in this step."""


class AbsolutePathLink(ResolutionLink):
    """Resolves icon when icon_name is a direct absolute path."""

    def try_resolve(self, icon_name: str) -> ResolvedIcon | None:
        if icon_name.startswith("/"):
            path = Path(icon_name)
            if path.is_file():
                fmt = path.suffix.lstrip(".").lower()
                return ResolvedIcon(
                    icon_name=icon_name,
                    source=ResolutionSource.ABSOLUTE,
                    resolved_path=path,
                    format=fmt,
                )
        return None


class TargetThemeLink(ResolutionLink):
    """Resolves icon within the target theme."""

    def __init__(
        self,
        theme_name: str,
        theme_reader: ThemeReader,
        next_link: ResolutionLink | None = None,
    ) -> None:
        super().__init__(next_link)
        self.theme_name = theme_name
        self.theme_dirs = theme_reader.get_theme_paths(theme_name)

    def try_resolve(self, icon_name: str) -> ResolvedIcon | None:
        for theme_dir in self.theme_dirs:
            found = find_icon_in_directory(theme_dir, icon_name)
            if found is not None:
                fmt = found.suffix.lstrip(".").lower()
                return ResolvedIcon(
                    icon_name=icon_name,
                    source=ResolutionSource.TARGET_THEME,
                    source_theme=self.theme_name,
                    resolved_path=found,
                    format=fmt,
                )
        return None


class InheritedThemesLink(ResolutionLink):
    """Resolves icon across inherited themes according to the theme hierarchy."""

    def __init__(
        self,
        inheritance_chain: Sequence[str],
        theme_reader: ThemeReader,
        next_link: ResolutionLink | None = None,
    ) -> None:
        super().__init__(next_link)
        self.inheritance_chain = tuple(inheritance_chain)
        self.theme_reader = theme_reader

    def try_resolve(self, icon_name: str) -> ResolvedIcon | None:
        candidates = get_icon_name_candidates(icon_name)
        for theme in self.inheritance_chain:
            theme_dirs = self.theme_reader.get_theme_paths(theme)
            for cand in candidates:
                for theme_dir in theme_dirs:
                    found = find_icon_in_directory(theme_dir, cand)
                    if found is not None:
                        fmt = found.suffix.lstrip(".").lower()
                        return ResolvedIcon(
                            icon_name=icon_name,
                            source=ResolutionSource.INHERITED_THEME,
                            source_theme=theme,
                            resolved_path=found,
                            format=fmt,
                        )
        return None


class PixmapsLink(ResolutionLink):
    """Resolves icon within standard pixmap directories."""

    def __init__(
        self,
        pixmap_dirs: Sequence[Path] | None = None,
        next_link: ResolutionLink | None = None,
    ) -> None:
        super().__init__(next_link)
        self.pixmap_dirs = tuple(pixmap_dirs) if pixmap_dirs is not None else get_default_pixmap_dirs()

    def try_resolve(self, icon_name: str) -> ResolvedIcon | None:
        candidates = get_icon_name_candidates(icon_name)
        for cand in candidates:
            for pixmap_dir in self.pixmap_dirs:
                if not pixmap_dir.is_dir():
                    continue
                found = find_icon_in_directory(pixmap_dir, cand)
                if found is not None:
                    fmt = found.suffix.lstrip(".").lower()
                    return ResolvedIcon(
                        icon_name=icon_name,
                        source=ResolutionSource.PIXMAPS,
                        resolved_path=found,
                        format=fmt,
                    )
        return None


class OptApplicationsLink(ResolutionLink):
    """Dynamically resolves icon across /opt or custom application directories without hardcoding."""

    def __init__(
        self,
        opt_dirs: Sequence[Path] | None = None,
        next_link: ResolutionLink | None = None,
    ) -> None:
        super().__init__(next_link)
        self.opt_dirs = tuple(opt_dirs) if opt_dirs is not None else get_default_opt_dirs()

    def try_resolve(self, icon_name: str) -> ResolvedIcon | None:
        base_name = icon_name
        for ext in SUPPORTED_EXTENSIONS:
            if base_name.endswith(ext):
                base_name = base_name[: -len(ext)]
                break

        low_base = base_name.lower()

        for opt_dir in self.opt_dirs:
            if not opt_dir.is_dir():
                continue

            try:
                # Walk with safety against deep loops
                for root, _, files in os.walk(opt_dir, followlinks=False):
                    root_path = Path(root)
                    for f in files:
                        f_low = f.lower()
                        for ext in SUPPORTED_EXTENSIONS:
                            if f_low.endswith(ext):
                                stem = f_low[: -len(ext)]
                                if stem == low_base or low_base in stem:
                                    candidate = root_path / f
                                    if candidate.is_file():
                                        return ResolvedIcon(
                                            icon_name=icon_name,
                                            source=ResolutionSource.OPT,
                                            resolved_path=candidate,
                                            format=ext.lstrip("."),
                                        )
            except (PermissionError, OSError):
                continue
        return None


class IconResolver:
    """Coordinates the Chain of Responsibility to resolve icons."""

    def __init__(
        self,
        target_theme: str = "ACYLS",
        icon_dirs: Sequence[Path] | None = None,
        pixmap_dirs: Sequence[Path] | None = None,
        opt_dirs: Sequence[Path] | None = None,
    ) -> None:
        self.target_theme = target_theme
        self.theme_reader = ThemeReader(icon_dirs=icon_dirs)
        self.inheritance_chain = self.theme_reader.resolve_inheritance_chain(target_theme)

        # Build chain of responsibility
        opt_link = OptApplicationsLink(opt_dirs=opt_dirs)
        pixmaps_link = PixmapsLink(pixmap_dirs=pixmap_dirs, next_link=opt_link)
        inherited_link = InheritedThemesLink(
            self.inheritance_chain,
            self.theme_reader,
            next_link=pixmaps_link,
        )
        target_link = TargetThemeLink(
            self.target_theme,
            self.theme_reader,
            next_link=inherited_link,
        )
        self.chain_head: ResolutionLink = AbsolutePathLink(next_link=target_link)
        self.source_chain_head: ResolutionLink = AbsolutePathLink(next_link=inherited_link)

    def resolve(self, icon_name: str, skip_target_theme: bool = False) -> ResolvedIcon:
        """Resolves an icon by name through the configured chain.

        If skip_target_theme is True, skips looking in the target theme and resolves
        directly from inherited themes, pixmaps, or opt dirs.
        """
        if skip_target_theme:
            return self.source_chain_head.resolve(icon_name)
        return self.chain_head.resolve(icon_name)

