"""Pytest fixtures providing synthetic Linux desktop environments and SVG assets."""

from __future__ import annotations

from pathlib import Path
import pytest


@pytest.fixture
def mock_env(tmp_path: Path):
    """Creates a synthetic filesystem environment for testing icon resolution."""
    # 1. Desktop application directories
    apps_sys = tmp_path / "usr/share/applications"
    apps_user = tmp_path / "home/user/.local/share/applications"
    apps_sys.mkdir(parents=True, exist_ok=True)
    apps_user.mkdir(parents=True, exist_ok=True)

    # 2. Icon theme directories
    icons_sys = tmp_path / "usr/share/icons"
    icons_user = tmp_path / "home/user/.local/share/icons"
    icons_sys.mkdir(parents=True, exist_ok=True)
    icons_user.mkdir(parents=True, exist_ok=True)

    # 3. Pixmaps directory
    pixmaps_dir = tmp_path / "usr/share/pixmaps"
    pixmaps_dir.mkdir(parents=True, exist_ok=True)

    # 4. Opt directory
    opt_dir = tmp_path / "opt"
    opt_dir.mkdir(parents=True, exist_ok=True)

    # Create Themes:
    # ACYLS theme
    acyls_dir = icons_sys / "ACYLS"
    (acyls_dir / "scalable/apps").mkdir(parents=True, exist_ok=True)
    (acyls_dir / "index.theme").write_text(
        "[Icon Theme]\nName=ACYLS\nInherits=adwaita,hicolor\nComment=Monochrome theme\n",
        encoding="utf-8",
    )
    (acyls_dir / "scalable/apps/firefox.svg").write_text(
        '<svg viewBox="0 0 16 16"><path fill="#A0A0A0" d="M0 0h16v16H0z"/></svg>',
        encoding="utf-8",
    )

    # Adwaita theme
    adwaita_dir = icons_sys / "adwaita"
    (adwaita_dir / "scalable/apps").mkdir(parents=True, exist_ok=True)
    (adwaita_dir / "index.theme").write_text(
        "[Icon Theme]\nName=Adwaita\nInherits=hicolor\n",
        encoding="utf-8",
    )
    (adwaita_dir / "scalable/apps/org.gnome.Snapshot.svg").write_text(
        '<svg viewBox="0 0 32 32"><circle fill="#3584E4" cx="16" cy="16" r="10"/></svg>',
        encoding="utf-8",
    )

    # Hicolor theme
    hicolor_dir = icons_sys / "hicolor"
    (hicolor_dir / "scalable/apps").mkdir(parents=True, exist_ok=True)
    (hicolor_dir / "index.theme").write_text(
        "[Icon Theme]\nName=Hicolor\n",
        encoding="utf-8",
    )
    (hicolor_dir / "scalable/apps/vlc.svg").write_text(
        '<svg viewBox="0 0 48 48"><polygon fill="#FFA500" points="0,0 48,0 24,48"/></svg>',
        encoding="utf-8",
    )

    # Pixmaps
    (pixmaps_dir / "gimp.png").write_text("FAKE_PNG_DATA", encoding="utf-8")

    # Opt package with internal assets (like Postman or Electron)
    postman_dir = opt_dir / "Postman/app/resources"
    postman_dir.mkdir(parents=True, exist_ok=True)
    (postman_dir / "postman-icon.png").write_text("FAKE_OPT_PNG", encoding="utf-8")

    # Desktop files:
    # App 1: In ACYLS (firefox)
    (apps_sys / "firefox.desktop").write_text(
        "[Desktop Entry]\nName=Firefox Web Browser\nIcon=firefox\nType=Application\n",
        encoding="utf-8",
    )
    # App 2: In Adwaita (camera/snapshot) - missing in ACYLS
    (apps_sys / "org.gnome.Snapshot.desktop").write_text(
        "[Desktop Entry]\nName=Camera\nIcon=org.gnome.Snapshot\nType=Application\n",
        encoding="utf-8",
    )
    # App 3: In Hicolor (vlc) - missing in ACYLS
    (apps_sys / "vlc.desktop").write_text(
        "[Desktop Entry]\nName=VLC Media Player\nIcon=vlc\nType=Application\n",
        encoding="utf-8",
    )
    # App 4: In Pixmaps (gimp)
    (apps_sys / "gimp.desktop").write_text(
        "[Desktop Entry]\nName=GIMP Image Editor\nIcon=gimp\nType=Application\n",
        encoding="utf-8",
    )
    # App 5: In Opt (postman)
    (apps_user / "postman.desktop").write_text(
        "[Desktop Entry]\nName=Postman\nIcon=postman-icon\nType=Application\n",
        encoding="utf-8",
    )
    # App 6: Absolute icon path
    abs_icon = tmp_path / "custom_icon.svg"
    abs_icon.write_text('<svg fill="#123456"/>', encoding="utf-8")
    (apps_user / "custom.desktop").write_text(
        f"[Desktop Entry]\nName=Custom App\nIcon={abs_icon}\nType=Application\n",
        encoding="utf-8",
    )
    # App 7: No display
    (apps_sys / "hidden.desktop").write_text(
        "[Desktop Entry]\nName=Hidden App\nIcon=hidden-icon\nNoDisplay=true\n",
        encoding="utf-8",
    )
    # App 8: Missing entirely
    (apps_sys / "ghost.desktop").write_text(
        "[Desktop Entry]\nName=Ghost App\nIcon=ghost-non-existent\n",
        encoding="utf-8",
    )

    return {
        "root": tmp_path,
        "apps_dirs": (apps_user, apps_sys),
        "icon_dirs": (icons_user, icons_sys),
        "pixmap_dirs": (pixmaps_dir,),
        "opt_dirs": (opt_dir,),
    }
