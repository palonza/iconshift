# IconShift 🔄

**IconShift** is an open-source Python toolkit for auditing, resolving, generating, and adapting application icons for Linux desktop environments.

It can transform existing SVG icons to match monochrome or custom color palettes while preserving their original geometry, transparency, and visual structure. **ACYLS** is supported as the default target theme, while other icon themes can be selected explicitly.

![Python](https://img.shields.io/badge/Python-3.12%2B-blue)
![Platform](https://img.shields.io/badge/platform-Linux-lightgrey)
![GitHub License](https://img.shields.io/github/license/palonza/iconshift)
![GitHub Release](https://img.shields.io/github/v/release/palonza/iconshift)

[Installation](#installation) · [Quick Start](#quick-start) · [Usage](#usage) · [Development](#development) · [Contributing](#contributing)

---

## Overview

IconShift discovers application icons dynamically instead of relying on hardcoded application names.

It follows the **Freedesktop Icon Theme Specification**, resolving the transitive `Inherits=` chain defined by `index.theme` down to fallback themes such as `hicolor`.

IconShift can also locate application icons stored outside the standard icon-theme hierarchy, including locations such as:

```text
/usr/share/pixmaps/
/opt/
```

The goal is to provide a predictable and scriptable way to identify missing application icons, locate suitable source assets, transform them, and install the resulting icons safely at user level.

---

## Features

### Application Icon Auditing

The `scan` command analyzes system and user `.desktop` files, determines how their icons are resolved, identifies icons missing from the target theme, and locates suitable source files.

### Unix-Friendly Output

Results can be displayed as human-readable tables or exported using structured formats:

* `tsv`
* `csv`
* `json`
* `paths`
* `icons`

This makes IconShift suitable for pipelines using tools such as `cut`, `awk`, `grep`, `xargs`, and `jq`.

### SVG Generation and Recoloring

The `generate` command transforms SVG icons while preserving:

* geometry
* opacity
* `none` values
* transparent elements

Both monochrome and two-tone transformations are supported.

### Safe User-Level Installation

Generated icons are stored at user level by default:

```text
~/.local/share/icons/<theme>/scalable/apps/
```

IconShift avoids modifying system-managed icon files under `/usr/share/` by default and does not require `sudo` for normal user-level operation.

### Palette Introspection

The `palette` command analyzes installed icon themes and extracts hexadecimal color frequencies to help determine their dominant visual palette.

### Isolated Testing

The project includes an automated test suite designed to run in an isolated virtualized environment.

---

## Project Status

IconShift is under active development.

The current implementation focuses primarily on Linux desktop environments using the Freedesktop icon-theme conventions, with GNOME/GTK as the initial desktop integration target.

Additional desktop environments and icon transformation strategies may be added in future releases.

---

## Installation

### Environment & Target Theme Setup (Arch Linux)

Before running IconShift with the default ACYLS theme, ensure the base build dependencies, AUR helper, and the ACYLS icon theme are installed:

1. **Install base development tools and AUR helper (`yay`):**
   ```bash
   sudo pacman -S --needed base-devel git
   git clone https://aur.archlinux.org/yay.git
   cd yay && makepkg -si && cd ..
   ```

2. **Install the ACYLS icon theme from AUR:**
   ```bash
   yay -S acyls-icon-theme-git
   ```

3. **Verify installed icon themes:**
   ```bash
   find /usr/share/icons ~/.icons ~/.local/share/icons -maxdepth 2 -name "index.theme" 2>/dev/null | awk -F'/' '{print $(NF-1)}' | sort -u
   ```

4. **Inspect and activate ACYLS in GNOME:**
   ```bash
   # Check currently active theme
   gsettings get org.gnome.desktop.interface icon-theme

   # Set active theme to ACYLS
   gsettings set org.gnome.desktop.interface icon-theme 'ACYLS'
   ```

### Arch Linux / AUR Package

Once the AUR package is published:

```bash
yay -S iconshift
```

Then run:

```bash
iconshift --help
```

### Binary Release

Precompiled standalone binaries can be obtained from the project's GitHub Releases.

After installation, IconShift can be invoked directly:

```bash
iconshift --version
```

### Running from Source

IconShift uses `uv` for fast Python packaging and dependency management.

1. **Install `uv`:**
   - On Arch Linux via pacman:
     ```bash
     sudo pacman -S uv
     ```
   - Or via the official installer:
     ```bash
     curl -LsSf https://astral.sh/uv/install.sh | sh
     ```

2. **Clone the repository and synchronize the environment:**
   ```bash
   # HTTPS
   git clone https://github.com/palonza/iconshift.git
   # or SSH: git clone git@github.com:palonza/iconshift.git

   cd iconshift
   uv sync
   ```

3. **Execute directly:**
   ```bash
   uv run iconshift --help
   ```

---

## Quick Start

Audit application icons:

```bash
iconshift scan
```

Find icons missing from the default target theme:

```bash
iconshift scan --missing
```

Preview what IconShift would generate without modifying any files:

```bash
iconshift generate --all --dry-run
```

Generate all missing icons:

```bash
iconshift generate --all
```

Inspect the palette of an installed theme:

```bash
iconshift palette --theme ACYLS
```

---

# Usage

## `scan` — Audit Application Icons

### Display all discovered application launchers and their resolved icons

```bash
iconshift scan
```

### Show only icons missing from ACYLS

```bash
iconshift scan --missing
```

### Audit against another icon theme

```bash
iconshift scan --theme Papirus --missing
```

### Produce Unix-friendly output

TSV without a header:

```bash
iconshift scan --missing --format tsv
```

Extract only resolved source paths:

```bash
iconshift scan --missing --format tsv | cut -f4
```

### JSON output

```bash
iconshift scan --missing --format json | jq .
```

---

## `generate` — Generate and Recolor Icons

### Dry run

Preview all operations without creating or modifying files:

```bash
iconshift generate --all --dry-run
```

### Generate all missing icons

IconShift automatically uses the adaptive palette detected for the target theme:

```bash
iconshift generate --all
```

### Force Regeneration

Regenerate and overwrite existing icons:

```bash
iconshift generate --all --force
```

### Color Transformation Modes

IconShift defaults to an **adaptive dominant** coloring strategy: identifying the primary visual container/background shape (mapping it to the theme's primary silver `#A0A0A0`) and contrasting glyphs/controls/emblems (mapping them to dark graphite `#404040`).

```bash
# Adaptive mode (default)
iconshift generate --all --adaptive

# Single-tone flat monochrome
iconshift generate --all --monochrome

# Custom two-tone with explicit colors
iconshift generate --all \
  --color "#A0A0A0" \
  --secondary-color "#404040" \
  --two-tone
```

### Generate a specific icon

```bash
iconshift generate --icon org.gnome.Snapshot
```

### Generate from a specific SVG file

```bash
iconshift generate --file /usr/share/icons/hicolor/scalable/apps/vlc.svg
```

### Custom monochrome color

```bash
iconshift generate --icon org.gnome.Snapshot --color "#00FFCC"
```

### Custom output directory

```bash
iconshift generate --all --output-dir ~/my-icon-theme/
```

### Unix pipelines

The output of `scan` can be piped directly into `generate`.

Preview a small batch with `head` and `--dry-run`:

```bash
iconshift scan --missing --format paths | head -n 3 | iconshift generate - --dry-run
```

Generate all scanned missing icons via pipe:

```bash
iconshift scan --missing --format paths | iconshift generate -
```

---

## `palette` — Inspect Theme Color Palettes

Analyze the most frequently used colors in an installed icon theme:

```bash
iconshift palette --theme ACYLS
```

Display the 30 most frequent colors:

```bash
iconshift palette --theme ACYLS --limit 30
```

---

## Desktop Integration

By default, generated icons are placed under:

```text
~/.local/share/icons/ACYLS/scalable/apps/
```

Refresh the icon cache:

```bash
# User-level cache (no sudo required):
gtk-update-icon-cache -f ~/.local/share/icons/ACYLS

# Or system-level cache:
sudo gtk-update-icon-cache -f /usr/share/icons/ACYLS
```

If the desktop environment does not immediately reflect the changes, reload or reapply the active icon theme:

```bash
gsettings set org.gnome.desktop.interface icon-theme 'ACYLS'
```

---

## Development

The project uses Python and `uv`.

Install development dependencies:

```bash
uv sync
```

Run IconShift from the source tree:

```bash
uv run iconshift --help
```

Build standalone executable:

```bash
make build
make install
```

### Automated Tests

The repository includes scripts for running the test suite in an isolated KVM/libvirt virtual machine:

```bash
make test
# or: ./scripts/test/run_tests_in_vm.sh
```

See [`scripts/README.md`](scripts/README.md) for details about the virtualized test environment and build automation.

---

## Safety

IconShift is designed to minimize changes to system-managed resources.

By default:

* generated icons are installed in the user's local icon hierarchy;
* files under `/usr/share/` are not overwritten;
* normal operations do not require root privileges;
* potentially destructive transformations can be inspected using `--dry-run`.

---

## Contributing

Contributions, bug reports, and feature requests are welcome.

Before submitting changes, make sure the relevant tests pass and that new behavior is covered by appropriate test cases.

See `CONTRIBUTING.md` for development and contribution guidelines.

---

## License

IconShift is open-source software.

See the [`LICENSE`](LICENSE) file for licensing details.
