"""Unit tests for the desktop applications scanner."""

from pathlib import Path

from iconshift.models import ResolutionSource
from iconshift.resolver import IconResolver
from iconshift.scanner import DesktopScanner, get_default_applications_dirs


def test_get_default_applications_dirs():
    dirs = get_default_applications_dirs()
    assert len(dirs) > 0


def test_parse_desktop_file_invalid(tmp_path: Path):
    scanner = DesktopScanner(applications_dirs=[tmp_path])

    # Missing file
    assert scanner.parse_desktop_file(tmp_path / "does_not_exist.desktop") is None

    # Empty file
    empty = tmp_path / "empty.desktop"
    empty.write_text("", encoding="utf-8")
    assert scanner.parse_desktop_file(empty) is None

    # Only name, no icon
    no_icon = tmp_path / "no_icon.desktop"
    no_icon.write_text("[Desktop Entry]\nName=OnlyName\n", encoding="utf-8")
    assert scanner.parse_desktop_file(no_icon) is None


def test_scanner_with_mock_env(mock_env):
    resolver = IconResolver(
        target_theme="ACYLS",
        icon_dirs=mock_env["icon_dirs"],
        pixmap_dirs=mock_env["pixmap_dirs"],
        opt_dirs=mock_env["opt_dirs"],
    )
    scanner = DesktopScanner(
        applications_dirs=mock_env["apps_dirs"],
        resolver=resolver,
    )

    # 1. Standard scan without hidden entries
    entries = scanner.scan_desktop_entries(include_hidden=False)
    entry_names = {e.name for e in entries}
    assert "Firefox Web Browser" in entry_names
    assert "Camera" in entry_names
    assert "VLC Media Player" in entry_names
    assert "Hidden App" not in entry_names

    # 2. Scan with hidden entries included
    entries_with_hidden = scanner.scan_desktop_entries(include_hidden=True)
    entry_names_all = {e.name for e in entries_with_hidden}
    assert "Hidden App" in entry_names_all

    # 3. Scan and resolve - ALL
    all_resolved = scanner.scan_and_resolve(missing_only=False)
    names_dict = {entry.name: resolved for entry, resolved in all_resolved}

    assert names_dict["Firefox Web Browser"].source == ResolutionSource.TARGET_THEME
    assert names_dict["Camera"].source == ResolutionSource.INHERITED_THEME
    assert names_dict["VLC Media Player"].source == ResolutionSource.INHERITED_THEME
    assert names_dict["GIMP Image Editor"].source == ResolutionSource.PIXMAPS
    assert names_dict["Postman"].source == ResolutionSource.OPT
    assert names_dict["Ghost App"].source == ResolutionSource.NOT_FOUND

    # 4. Scan and resolve - MISSING ONLY
    # Must only contain items that are resolved on the system BUT missing in ACYLS
    missing_resolved = scanner.scan_and_resolve(missing_only=True)
    missing_app_names = [entry.name for entry, _ in missing_resolved]

    # Firefox is in ACYLS -> MUST NOT be in missing
    assert "Firefox Web Browser" not in missing_app_names
    # Ghost is not resolved anywhere -> MUST NOT be in missing
    assert "Ghost App" not in missing_app_names

    # Camera, VLC, GIMP, Postman must be present
    assert "Camera" in missing_app_names
    assert "VLC Media Player" in missing_app_names
    assert "GIMP Image Editor" in missing_app_names
    assert "Postman" in missing_app_names
