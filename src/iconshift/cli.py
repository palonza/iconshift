"""Command-Line Interface entry point for IconShift."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from iconshift import __version__
from iconshift.commands import GenerateCommand, PaletteCommand, ScanCommand
from iconshift.formatters import (
    CsvFormatter,
    IconOnlyFormatter,
    JsonFormatter,
    OutputFormatter,
    PathOnlyFormatter,
    TableFormatter,
    TsvFormatter,
)


def create_parser() -> argparse.ArgumentParser:
    """Constructs the argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="iconshift",
        description="Universal icon resolver and theme generator for Linux desktop environments.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # 1. scan
    scan_parser = subparsers.add_parser(
        "scan",
        help="Scan desktop applications and audit icon resolution against a theme.",
    )
    scan_parser.add_argument(
        "--theme",
        default="ACYLS",
        help="Target icon theme to check coverage against (default: ACYLS).",
    )
    scan_parser.add_argument(
        "--missing",
        action="store_true",
        help="Filter only icons missing in target theme but resolved elsewhere in the system.",
    )
    scan_parser.add_argument(
        "--format",
        choices=["table", "tsv", "csv", "json", "paths", "icons"],
        default="table",
        help="Output format (default: table).",
    )
    scan_parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include desktop entries marked as NoDisplay.",
    )

    # 2. generate
    gen_parser = subparsers.add_parser(
        "generate",
        help="Generate and recolor missing icons to match theme aesthetics.",
    )
    gen_parser.add_argument(
        "stdin_arg",
        nargs="?",
        default=None,
        help="Use '-' to read icon paths or names from standard input.",
    )
    gen_parser.add_argument(
        "--theme",
        default="ACYLS",
        help="Target icon theme (default: ACYLS).",
    )
    gen_parser.add_argument(
        "--icon",
        help="Name of a single icon to resolve and generate.",
    )
    gen_parser.add_argument(
        "--file",
        type=Path,
        help="Path to an explicit SVG icon file to recolor and install.",
    )
    gen_parser.add_argument(
        "--all",
        action="store_true",
        help="Generate all icons currently missing in the target theme.",
    )
    gen_parser.add_argument(
        "--color",
        "-c",
        help="Primary color in hex format (e.g. #A0A0A0). Defaults to theme palette.",
    )
    gen_parser.add_argument(
        "--secondary-color",
        "-s",
        help="Secondary color in hex format for two-tone depth (e.g. #404040).",
    )
    gen_parser.add_argument(
        "--two-tone",
        action="store_true",
        help="Enable two-tone mapping (light colors to primary, dark colors to secondary).",
    )
    gen_parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        help="Destination directory. Defaults to ~/.local/share/icons/<theme>/scalable/apps.",
    )
    gen_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate icon generation without writing any files to disk.",
    )

    # 3. palette
    pal_parser = subparsers.add_parser(
        "palette",
        help="Inspect colors and extract the dominant palette of an icon theme.",
    )
    pal_parser.add_argument(
        "--theme",
        default="ACYLS",
        help="Icon theme to inspect (default: ACYLS).",
    )
    pal_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of top frequent colors to display (default: 20).",
    )

    return parser


def get_formatter(format_name: str) -> OutputFormatter:
    """Returns the corresponding OutputFormatter strategy."""
    formatters: dict[str, OutputFormatter] = {
        "table": TableFormatter(),
        "tsv": TsvFormatter(),
        "csv": CsvFormatter(),
        "json": JsonFormatter(),
        "paths": PathOnlyFormatter(),
        "icons": IconOnlyFormatter(),
    }
    return formatters.get(format_name, TableFormatter())


def main(argv: Sequence[str] | None = None) -> int:
    """Main CLI execution dispatching to commands."""
    try:
        parser = create_parser()
        args = parser.parse_args(argv)

        if args.subcommand == "scan":
            formatter = get_formatter(args.format)
            cmd = ScanCommand(
                theme=args.theme,
                missing_only=args.missing,
                formatter=formatter,
                include_hidden=args.include_hidden,
            )
            return cmd.execute()

        if args.subcommand == "generate":
            from_stdin = args.stdin_arg == "-" or not sys.stdin.isatty() if not any([args.icon, args.file, args.all]) else False
            if args.stdin_arg == "-":
                from_stdin = True

            cmd = GenerateCommand(
                theme=args.theme,
                icon_name=args.icon,
                file_path=args.file,
                all_missing=args.all,
                from_stdin=from_stdin,
                color=args.color,
                secondary_color=args.secondary_color,
                two_tone=args.two_tone,
                output_dir=args.output_dir,
                dry_run=args.dry_run,
            )
            return cmd.execute()

        if args.subcommand == "palette":
            cmd = PaletteCommand(
                theme=args.theme,
                limit=args.limit,
            )
            return cmd.execute()

        return 0
    except BrokenPipeError:
        try:
            sys.stderr.close()
        except Exception:
            pass
        return 0


if __name__ == "__main__":
    sys.exit(main())
