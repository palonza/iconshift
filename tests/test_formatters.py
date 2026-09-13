"""Unit tests for terminal output formatters."""

import json
from pathlib import Path

from iconshift.formatters import (
    CsvFormatter,
    IconOnlyFormatter,
    JsonFormatter,
    PathOnlyFormatter,
    TableFormatter,
    TsvFormatter,
)
from iconshift.models import DesktopEntry, ResolutionSource, ResolvedIcon


def sample_items():
    entry1 = DesktopEntry(
        desktop_path=Path("/usr/share/applications/firefox.desktop"),
        name="Firefox",
        icon_name="firefox",
    )
    res1 = ResolvedIcon(
        icon_name="firefox",
        source=ResolutionSource.TARGET_THEME,
        source_theme="ACYLS",
        resolved_path=Path("/usr/share/icons/ACYLS/scalable/apps/firefox.svg"),
        format="svg",
    )

    entry2 = DesktopEntry(
        desktop_path=Path("/usr/share/applications/vlc.desktop"),
        name="VLC",
        icon_name="vlc",
    )
    res2 = ResolvedIcon(
        icon_name="vlc",
        source=ResolutionSource.INHERITED_THEME,
        source_theme="hicolor",
        resolved_path=Path("/usr/share/icons/hicolor/scalable/apps/vlc.svg"),
        format="svg",
    )
    return [(entry1, res1), (entry2, res2)]


def test_table_formatter():
    fmt = TableFormatter()
    empty_out = fmt.render([])
    assert "No matching" in empty_out

    out = fmt.render(sample_items())
    assert "APPLICATION" in out
    assert "ICON NAME" in out
    assert "Firefox" in out
    assert "VLC" in out


def test_tsv_formatter():
    fmt = TsvFormatter(include_header=True)
    out = fmt.render(sample_items())
    lines = out.split("\n")
    assert lines[0] == "name\ticon\tsource\tpath"
    assert "Firefox\tfirefox\tACYLS\t/usr/share/icons/ACYLS/scalable/apps/firefox.svg" in lines[1]


def test_csv_formatter():
    fmt = CsvFormatter(include_header=True)
    out = fmt.render(sample_items())
    assert "name,icon,source,path" in out
    assert "Firefox,firefox,ACYLS,/usr/share/icons/ACYLS/scalable/apps/firefox.svg" in out


def test_json_formatter():
    fmt = JsonFormatter()
    out = fmt.render(sample_items())
    data = json.loads(out)
    assert len(data) == 2
    assert data[0]["name"] == "Firefox"
    assert data[0]["source"] == "target_theme"
    assert data[1]["name"] == "VLC"
    assert data[1]["is_missing_in_target"] is True


def test_path_only_formatter():
    fmt = PathOnlyFormatter()
    out = fmt.render(sample_items())
    lines = out.split("\n")
    assert len(lines) == 2
    assert lines[0].endswith("firefox.svg")
    assert lines[1].endswith("vlc.svg")


def test_icon_only_formatter():
    fmt = IconOnlyFormatter()
    out = fmt.render(sample_items())
    lines = out.split("\n")
    assert lines == ["firefox", "vlc"]
