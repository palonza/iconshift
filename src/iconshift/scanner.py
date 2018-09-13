"""Desktop file scanner to discover and audit applications."""

from __future__ import annotations

import configparser
from pathlib import Path
from typing import Sequence

from iconshift.models import DesktopEntry, ResolvedIcon
from iconshift.resolver import IconResolver


def get_default_applications_dirs() -> tuple[Path, ...]:
    """Default directories where .desktop application files reside in Linux."""
    home = Path.home()
    return (
        home / ".local/share/applications",
        Path("/usr/local/share/applications"),
        Path("/usr/share/applications"),
    )


class DesktopScanner:
    """Discovers and parses .desktop application entries."""

    def __init__(
        self,
        applications_dirs: Sequence[Path] | None = None,
        resolver: IconResolver | None = None,
    ) -> None:
        self.applications_dirs = (
            tuple(applications_dirs)
            if applications_dirs is not None
            else get_default_applications_dirs()
        )
        self.resolver = resolver if resolver is not None else IconResolver()

    def parse_desktop_file(self, desktop_file: Path) -> DesktopEntry | None:
        """Parses a single .desktop file, returning None if invalid or uninteresting."""
        if not desktop_file.is_file():
            return None

        # Custom tolerant line-by-line reading to handle loose .desktop files
        name: str | None = None
        icon: str | None = None
        no_display = False
        terminal = False
        in_entry = False

        try:
            with open(desktop_file, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if line == "[Desktop Entry]":
                        in_entry = True
                        continue
                    if line.startswith("[") and in_entry:
                        # Another section started (e.g. [Desktop Action])
                        break
                    if in_entry and "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip()
                        if key == "Name" and name is None:
                            name = val
                        elif key == "Icon" and icon is None:
                            icon = val
                        elif key == "NoDisplay":
                            no_display = val.lower() == "true"
                        elif key == "Terminal":
                            terminal = val.lower() == "true"
        except OSError:
            return None

        if not name or not icon:
            return None

        return DesktopEntry(
            desktop_path=desktop_file,
            name=name,
            icon_name=icon,
            no_display=no_display,
            terminal=terminal,
        )

    def scan_desktop_entries(self, include_hidden: bool = False) -> list[DesktopEntry]:
        """Scans all desktop directories and yields valid application entries."""
        entries: list[DesktopEntry] = []
        seen_paths: set[Path] = set()

        for app_dir in self.applications_dirs:
            if not app_dir.is_dir():
                continue

            for desktop_file in sorted(app_dir.glob("*.desktop")):
                real_file = desktop_file.resolve()
                if real_file in seen_paths:
                    continue
                seen_paths.add(real_file)

                entry = self.parse_desktop_file(desktop_file)
                if entry is None:
                    continue
                if entry.no_display and not include_hidden:
                    continue
                entries.append(entry)

        return entries

    def scan_and_resolve(
        self,
        missing_only: bool = False,
        include_hidden: bool = False,
        deduplicate_icons: bool = True,
    ) -> list[tuple[DesktopEntry, ResolvedIcon]]:
        """Scans desktop entries and resolves each icon against the configured resolver."""
        raw_entries = self.scan_desktop_entries(include_hidden=include_hidden)
        results: list[tuple[DesktopEntry, ResolvedIcon]] = []
        seen_icons: set[str] = set()

        for entry in raw_entries:
            if deduplicate_icons:
                if entry.icon_name in seen_icons:
                    continue
                seen_icons.add(entry.icon_name)

            resolved = self.resolver.resolve(entry.icon_name)

            if missing_only:
                if resolved.is_missing_in_target:
                    results.append((entry, resolved))
            else:
                results.append((entry, resolved))

        return results
