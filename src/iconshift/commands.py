"""Command pattern implementations for IconShift CLI operations."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

from iconshift.colorizer import SvgPipeline
from iconshift.formatters import OutputFormatter
from iconshift.models import ColorConfig
from iconshift.palette import PaletteInspector
from iconshift.resolver import IconResolver
from iconshift.scanner import DesktopScanner


class Command(Protocol):
    """Protocol for executable commands."""

    def execute(self) -> int:
        """Executes the command and returns an exit code."""
        ...


@dataclass
class ColorizeIconCommand:
    """Atomic command to recolor and install a single SVG icon."""

    source_path: Path
    destination_path: Path
    pipeline: SvgPipeline
    dry_run: bool = False

    def execute(self) -> bool:
        """Executes the colorization. Returns True on success."""
        if not self.source_path.is_file():
            print(f"[ERROR] Source file not found: {self.source_path}", file=sys.stderr)
            return False

        if not self.source_path.name.lower().endswith(".svg"):
            print(
                f"[SKIP] Currently only SVG vector icons can be recolored ({self.source_path})",
                file=sys.stderr,
            )
            return False

        if self.dry_run:
            print(f"[DRY-RUN] Would generate: {self.destination_path} from {self.source_path}")
            return True

        try:
            self.pipeline.colorize_file(self.source_path, self.destination_path)
            print(f"[OK] Generated: {self.destination_path}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to colorize {self.source_path}: {e}", file=sys.stderr)
            return False


class ScanCommand:
    """Command to scan desktop applications and audit icon resolution."""

    def __init__(
        self,
        theme: str = "ACYLS",
        missing_only: bool = False,
        formatter: OutputFormatter | None = None,
        include_hidden: bool = False,
        scanner: DesktopScanner | None = None,
    ) -> None:
        self.theme = theme
        self.missing_only = missing_only
        self.include_hidden = include_hidden
        self.scanner = (
            scanner
            if scanner is not None
            else DesktopScanner(resolver=IconResolver(target_theme=theme))
        )
        self.formatter = formatter

    def execute(self) -> int:
        from iconshift.formatters import TableFormatter

        formatter = self.formatter if self.formatter is not None else TableFormatter()
        results = self.scanner.scan_and_resolve(
            missing_only=self.missing_only,
            include_hidden=self.include_hidden,
        )
        output = formatter.render(results)
        if output:
            print(output)
        return 0


class GenerateCommand:
    """Command to generate recolored icons from missing sources or files."""

    def __init__(
        self,
        theme: str = "ACYLS",
        icon_name: str | None = None,
        file_path: Path | None = None,
        all_missing: bool = False,
        from_stdin: bool = False,
        color: str | None = None,
        secondary_color: str | None = None,
        two_tone: bool = False,
        output_dir: Path | None = None,
        dry_run: bool = False,
        resolver: IconResolver | None = None,
        scanner: DesktopScanner | None = None,
    ) -> None:
        self.theme = theme
        self.icon_name = icon_name
        self.file_path = file_path
        self.all_missing = all_missing
        self.from_stdin = from_stdin
        self.color = color
        self.secondary_color = secondary_color
        self.two_tone = two_tone
        self.dry_run = dry_run

        self.resolver = resolver if resolver is not None else IconResolver(target_theme=theme)
        self.scanner = scanner if scanner is not None else DesktopScanner(resolver=self.resolver)

        # Default output directory: ~/.local/share/icons/<theme>/scalable/apps
        if output_dir is not None:
            self.output_dir = output_dir
        else:
            self.output_dir = Path.home() / ".local/share/icons" / theme / "scalable/apps"

    def execute(self) -> int:
        # Determine colors: if not specified, detect from theme or use default ACYLS
        primary = self.color
        secondary = self.secondary_color

        if not primary:
            inspector = PaletteInspector(theme_reader=self.resolver.theme_reader)
            primary, detected_sec = inspector.detect_palette(self.theme)
            if not secondary:
                secondary = detected_sec

        if not secondary:
            secondary = "#404040"

        config = ColorConfig(
            primary=primary,
            secondary=secondary,
            two_tone=self.two_tone,
        )
        pipeline = SvgPipeline(config=config)

        targets_to_generate: list[tuple[Path, Path]] = []

        # Case 1: Read from standard input
        if self.from_stdin:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                p = Path(line)
                if p.is_file():
                    dest = self.output_dir / p.name
                    targets_to_generate.append((p, dest))
                else:
                    # Treat as icon name
                    resolved = self.resolver.resolve(line)
                    if resolved.resolved_path and resolved.resolved_path.is_file():
                        base_name = Path(line).name
                        if not base_name.endswith(".svg"):
                            base_name = f"{base_name}.svg"
                        dest = self.output_dir / base_name
                        targets_to_generate.append((resolved.resolved_path, dest))
                    else:
                        print(f"[WARN] Could not resolve icon: {line}", file=sys.stderr)

        # Case 2: Specific file provided
        elif self.file_path is not None:
            dest = self.output_dir / self.file_path.name
            targets_to_generate.append((self.file_path, dest))

        # Case 3: Specific icon name provided
        elif self.icon_name is not None:
            resolved = self.resolver.resolve(self.icon_name)
            if resolved.resolved_path and resolved.resolved_path.is_file():
                base_name = Path(self.icon_name).name
                if not base_name.endswith(".svg"):
                    base_name = f"{base_name}.svg"
                dest = self.output_dir / base_name
                targets_to_generate.append((resolved.resolved_path, dest))
            else:
                print(
                    f"[ERROR] Icon '{self.icon_name}' could not be resolved from any system source.",
                    file=sys.stderr,
                )
                return 1

        # Case 4: All missing icons
        elif self.all_missing:
            missing_items = self.scanner.scan_and_resolve(missing_only=True)
            for entry, resolved in missing_items:
                if resolved.resolved_path and resolved.resolved_path.is_file():
                    # Only vector SVG icons can be recolored for the scalable theme
                    if not resolved.resolved_path.name.lower().endswith(".svg"):
                        continue
                    base_name = Path(entry.icon_name).name
                    if not base_name.endswith(".svg"):
                        base_name = f"{base_name}.svg"
                    dest = self.output_dir / base_name
                    targets_to_generate.append((resolved.resolved_path, dest))

        else:
            print(
                "[ERROR] Please specify an icon (--icon), file (--file), --all, or pipe inputs (-).",
                file=sys.stderr,
            )
            return 2

        if not targets_to_generate:
            print("No icons to generate.")
            return 0

        success_count = 0
        for src, dst in targets_to_generate:
            cmd = ColorizeIconCommand(
                source_path=src,
                destination_path=dst,
                pipeline=pipeline,
                dry_run=self.dry_run,
            )
            if cmd.execute():
                success_count += 1

        total = len(targets_to_generate)
        action = "Simulated" if self.dry_run else "Generated"
        print(f"\n{action} {success_count}/{total} icons.")
        return 0 if success_count == total else 1


class PaletteCommand:
    """Command to inspect and display a theme's color palette."""

    def __init__(
        self,
        theme: str = "ACYLS",
        limit: int = 20,
        inspector: PaletteInspector | None = None,
    ) -> None:
        self.theme = theme
        self.limit = limit
        self.inspector = inspector if inspector is not None else PaletteInspector()

    def execute(self) -> int:
        top_colors = self.inspector.get_top_colors(self.theme, limit=self.limit)
        if not top_colors:
            print(f"No SVG colors detected for theme '{self.theme}'.")
            return 0

        print(f"Top {len(top_colors)} colors in theme '{self.theme}':")
        print(f"{'COLOR HEX':<12} | {'OCCURRENCES':<12}")
        print(f"{'-'*12}-+-{'-'*12}")
        for color, count in top_colors:
            print(f"{color:<12} | {count:<12}")

        primary, secondary = self.inspector.detect_palette(self.theme)
        print(f"\nDetected Palette -> Primary: {primary} | Secondary: {secondary}")
        return 0
