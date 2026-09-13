"""Unit tests for the icon resolution engine and theme inheritance."""

from pathlib import Path

from iconshift.models import ResolutionSource
from iconshift.resolver import (
    IconResolver,
    ThemeReader,
    find_icon_in_directory,
    get_default_icon_dirs,
    get_default_opt_dirs,
    get_default_pixmap_dirs,
)


def test_default_directories_return_paths():
    assert len(get_default_icon_dirs()) > 0
    assert len(get_default_pixmap_dirs()) > 0
    assert len(get_default_opt_dirs()) > 0


def test_theme_reader_inheritance(mock_env):
    reader = ThemeReader(icon_dirs=mock_env["icon_dirs"])

    # Metadata
    acyls_meta = reader.read_metadata("ACYLS")
    assert acyls_meta.name == "ACYLS"
    assert acyls_meta.inherits == ("adwaita", "hicolor")
    assert acyls_meta.comment == "Monochrome theme"

    # Transitive inheritance
    chain = reader.resolve_inheritance_chain("ACYLS")
    assert chain == ("adwaita", "hicolor")

    # When theme has no inherits, fallback to hicolor is preserved
    empty_chain = reader.resolve_inheritance_chain("non-existent-theme")
    assert empty_chain == ("hicolor",)


def test_find_icon_in_directory(tmp_path: Path):
    d = tmp_path / "icons"
    d.mkdir()
    (d / "sample.svg").write_text("SVG", encoding="utf-8")
    (d / "sample.png").write_text("PNG", encoding="utf-8")

    # SVG preferred
    found = find_icon_in_directory(d, "sample")
    assert found is not None
    assert found.suffix == ".svg"

    # With extension in query
    found_ext = find_icon_in_directory(d, "sample.svg")
    assert found_ext is not None
    assert found_ext.name == "sample.svg"

    # Non-existent
    assert find_icon_in_directory(d, "unknown") is None


def test_resolver_chain_all_links(mock_env):
    resolver = IconResolver(
        target_theme="ACYLS",
        icon_dirs=mock_env["icon_dirs"],
        pixmap_dirs=mock_env["pixmap_dirs"],
        opt_dirs=mock_env["opt_dirs"],
    )

    # 1. Target theme link (firefox)
    res_firefox = resolver.resolve("firefox")
    assert res_firefox.source == ResolutionSource.TARGET_THEME
    assert res_firefox.source_theme == "ACYLS"
    assert res_firefox.is_in_target_theme is True
    assert res_firefox.format == "svg"

    # 2. Inherited theme link - 1st tier (camera / org.gnome.Snapshot in adwaita)
    res_snapshot = resolver.resolve("org.gnome.Snapshot")
    assert res_snapshot.source == ResolutionSource.INHERITED_THEME
    assert res_snapshot.source_theme == "adwaita"
    assert res_snapshot.is_missing_in_target is True

    # 3. Inherited theme link - 2nd tier (vlc in hicolor)
    res_vlc = resolver.resolve("vlc")
    assert res_vlc.source == ResolutionSource.INHERITED_THEME
    assert res_vlc.source_theme == "hicolor"
    assert res_vlc.is_missing_in_target is True

    # 4. Pixmaps link (gimp)
    res_gimp = resolver.resolve("gimp")
    assert res_gimp.source == ResolutionSource.PIXMAPS
    assert res_gimp.is_missing_in_target is True

    # 5. Opt applications link (postman-icon)
    res_postman = resolver.resolve("postman-icon")
    assert res_postman.source == ResolutionSource.OPT
    assert res_postman.is_missing_in_target is True

    # 6. Absolute path
    abs_svg = mock_env["root"] / "custom_icon.svg"
    res_abs = resolver.resolve(str(abs_svg))
    assert res_abs.source == ResolutionSource.ABSOLUTE
    assert res_abs.resolved_path == abs_svg

    # 7. Not found
    res_ghost = resolver.resolve("ghost-non-existent")
    assert res_ghost.source == ResolutionSource.NOT_FOUND
    assert res_ghost.resolved_path is None
    assert res_ghost.is_resolved is False
