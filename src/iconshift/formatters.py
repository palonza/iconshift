"""Terminal and data formatters implementing the Strategy pattern."""

from __future__ import annotations

import csv
import io
import json
from abc import ABC, abstractmethod
from typing import Sequence

from iconshift.models import DesktopEntry, ResolvedIcon


class OutputFormatter(ABC):
    """Abstract Strategy for rendering scan results."""

    @abstractmethod
    def render(self, items: Sequence[tuple[DesktopEntry, ResolvedIcon]]) -> str:
        """Formats the list of scanned applications and resolved icons."""


class TableFormatter(OutputFormatter):
    """Human-friendly tabular output with aligned columns."""

    def render(self, items: Sequence[tuple[DesktopEntry, ResolvedIcon]]) -> str:
        if not items:
            return "No matching desktop icons found."

        rows = []
        for entry, resolved in items:
            source_label = resolved.source_theme or resolved.source.label()
            res_path = str(resolved.resolved_path) if resolved.resolved_path else "NO ENCONTRADO"
            rows.append((entry.name, entry.icon_name, source_label, res_path))

        # Calculate max column widths
        w_name = max(len("APPLICATION"), max(len(r[0]) for r in rows))
        w_icon = max(len("ICON NAME"), max(len(r[1]) for r in rows))
        w_src = max(len("SOURCE"), max(len(r[2]) for r in rows))

        w_name = min(w_name, 35)
        w_icon = min(w_icon, 40)
        w_src = min(w_src, 15)

        lines = [
            f"{'APPLICATION':<{w_name}} | {'ICON NAME':<{w_icon}} | {'SOURCE':<{w_src}} | {'RESOLVED PATH'}",
            f"{'-'*w_name}-+-{'-'*w_icon}-+-{'-'*w_src}-+-{'-'*30}",
        ]

        for name, icon, src, path in rows:
            lines.append(f"{name:<{w_name}} | {icon:<{w_icon}} | {src:<{w_src}} | {path}")

        return "\n".join(lines)


class TsvFormatter(OutputFormatter):
    """Tab-Separated Values, ideal for Unix pipelines (awk, cut)."""

    def __init__(self, include_header: bool = False) -> None:
        self.include_header = include_header

    def render(self, items: Sequence[tuple[DesktopEntry, ResolvedIcon]]) -> str:
        lines: list[str] = []
        if self.include_header:
            lines.append("name\ticon\tsource\tpath")

        for entry, resolved in items:
            src = resolved.source_theme or resolved.source.value
            path = str(resolved.resolved_path or "")
            lines.append(f"{entry.name}\t{entry.icon_name}\t{src}\t{path}")

        return "\n".join(lines)


class CsvFormatter(OutputFormatter):
    """Comma-Separated Values formatted using standard Python csv module."""

    def __init__(self, include_header: bool = True) -> None:
        self.include_header = include_header

    def render(self, items: Sequence[tuple[DesktopEntry, ResolvedIcon]]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        if self.include_header:
            writer.writerow(["name", "icon", "source", "path"])

        for entry, resolved in items:
            src = resolved.source_theme or resolved.source.value
            path = str(resolved.resolved_path or "")
            writer.writerow([entry.name, entry.icon_name, src, path])

        return output.getvalue().rstrip("\r\n")


class JsonFormatter(OutputFormatter):
    """JSON output for structured parsing (jq, APIs)."""

    def render(self, items: Sequence[tuple[DesktopEntry, ResolvedIcon]]) -> str:
        data = [
            {
                "name": entry.name,
                "desktop_file": str(entry.desktop_path),
                "icon_name": entry.icon_name,
                "source": resolved.source.value,
                "source_theme": resolved.source_theme,
                "resolved_path": str(resolved.resolved_path) if resolved.resolved_path else None,
                "format": resolved.format,
                "is_in_target_theme": resolved.is_in_target_theme,
                "is_missing_in_target": resolved.is_missing_in_target,
            }
            for entry, resolved in items
        ]
        return json.dumps(data, indent=2, ensure_ascii=False)


class PathOnlyFormatter(OutputFormatter):
    """Outputs only the resolved file path per line, ideal for piping into xargs or generator."""

    def render(self, items: Sequence[tuple[DesktopEntry, ResolvedIcon]]) -> str:
        paths = [
            str(resolved.resolved_path)
            for _, resolved in items
            if resolved.resolved_path is not None
        ]
        return "\n".join(paths)


class IconOnlyFormatter(OutputFormatter):
    """Outputs only the icon name per line."""

    def render(self, items: Sequence[tuple[DesktopEntry, ResolvedIcon]]) -> str:
        names = [entry.icon_name for entry, _ in items if entry.icon_name]
        return "\n".join(names)
