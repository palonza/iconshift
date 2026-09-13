"""Unit tests for models and DTOs."""

from pathlib import Path
import pytest
from dataclasses import FrozenInstanceError

from iconshift.models import (
    ColorConfig,
    DesktopEntry,
    ResolutionSource,
    ResolvedIcon,
    ThemeMetadata,
)


def test_resolution_source_labels():
    assert ResolutionSource.TARGET_THEME.label() == "TARGET"
    assert ResolutionSource.INHERITED_THEME.label() == "INHERITED"
    assert ResolutionSource.PIXMAPS.label() == "PIXMAPS"
    assert ResolutionSource.OPT.label() == "OPT"
    assert ResolutionSource.ABSOLUTE.label() == "ABSOLUTE"
    assert ResolutionSource.NOT_FOUND.label() == "NOT_FOUND"


def test_desktop_entry_properties():
    entry = DesktopEntry(
        desktop_path=Path("/usr/share/applications/test.desktop"),
        name="Test Application",
        icon_name="test-icon",
        no_display=False,
    )
    assert entry.has_icon is True
    assert entry.is_absolute_icon is False

    # Immutability check
    with pytest.raises(FrozenInstanceError):
        entry.name = "Modified"  # type: ignore

    # Absolute icon
    abs_entry = DesktopEntry(
        desktop_path=Path("/tmp/foo.desktop"),
        name="Foo",
        icon_name="/opt/foo/icon.png",
    )
    assert abs_entry.is_absolute_icon is True

    # Empty icon
    empty_entry = DesktopEntry(
        desktop_path=Path("/tmp/empty.desktop"),
        name="Empty",
        icon_name="  ",
    )
    assert empty_entry.has_icon is False


def test_resolved_icon_properties():
    # In target theme
    target_res = ResolvedIcon(
        icon_name="firefox",
        source=ResolutionSource.TARGET_THEME,
        source_theme="ACYLS",
        resolved_path=Path("/usr/share/icons/ACYLS/scalable/apps/firefox.svg"),
        format="svg",
    )
    assert target_res.is_resolved is True
    assert target_res.is_in_target_theme is True
    assert target_res.is_missing_in_target is False

    # Missing in target theme, but resolved in inherited theme
    inherited_res = ResolvedIcon(
        icon_name="camera",
        source=ResolutionSource.INHERITED_THEME,
        source_theme="adwaita",
        resolved_path=Path("/usr/share/icons/adwaita/scalable/apps/camera.svg"),
        format="svg",
    )
    assert inherited_res.is_resolved is True
    assert inherited_res.is_in_target_theme is False
    assert inherited_res.is_missing_in_target is True

    # Not found
    not_found = ResolvedIcon(
        icon_name="non-existent",
        source=ResolutionSource.NOT_FOUND,
    )
    assert not_found.is_resolved is False
    assert not_found.is_in_target_theme is False
    assert not_found.is_missing_in_target is False


def test_theme_metadata_immutability():
    meta = ThemeMetadata(
        name="ACYLS",
        theme_dirs=(Path("/usr/share/icons/ACYLS"),),
        inherits=("adwaita", "hicolor"),
    )
    assert meta.name == "ACYLS"
    assert meta.inherits == ("adwaita", "hicolor")
    with pytest.raises(FrozenInstanceError):
        meta.name = "Other"  # type: ignore


def test_color_config():
    default_cfg = ColorConfig()
    assert default_cfg.primary == "#A0A0A0"
    assert default_cfg.secondary == "#404040"
    assert default_cfg.two_tone is False

    custom_cfg = ColorConfig(
        primary="#112233",
        secondary="#445566",
        two_tone=True,
    )
    assert custom_cfg.primary == "#112233"
    assert custom_cfg.two_tone is True
