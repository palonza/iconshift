#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Prepare an AUR package update by modifying PKGBUILD and regenerating .SRCINFO.
This script does NOT perform git push or publish to AUR.

Options:
  -v, --version VERSION    Target package version (default: auto-detect from project)
  -s, --sha256 HASH        SHA-256 checksum of release tarball (default: auto-detect from release/)
  -p, --pkgbuild PATH      Path to target PKGBUILD file (default: looks in current dir or AUR repo)
  -d, --dir PATH           Path to directory containing PKGBUILD (alternative to --pkgbuild)
  -h, --help               Show this help message
EOF
}

VERSION=""
SHA256=""
PKGBUILD_PATH=""
TARGET_DIR=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        -s|--sha256)
            SHA256="$2"
            shift 2
            ;;
        -p|--pkgbuild)
            PKGBUILD_PATH="$2"
            shift 2
            ;;
        -d|--dir)
            TARGET_DIR="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "ERROR: Unknown option '$1'" >&2
            usage >&2
            exit 1
            ;;
    esac
done

# Resolve PKGBUILD location
if [[ -n "$TARGET_DIR" ]]; then
    PKGBUILD_PATH="$TARGET_DIR/PKGBUILD"
elif [[ -z "$PKGBUILD_PATH" ]]; then
    if [[ -f "./PKGBUILD" ]]; then
        PKGBUILD_PATH="./PKGBUILD"
    elif [[ -f "$PROJECT_ROOT/packaging/aur/PKGBUILD" ]]; then
        PKGBUILD_PATH="$PROJECT_ROOT/packaging/aur/PKGBUILD"
    else
        echo "ERROR: PKGBUILD not found. Please specify via --pkgbuild or --dir." >&2
        exit 1
    fi
fi

if [[ ! -f "$PKGBUILD_PATH" ]]; then
    echo "ERROR: Target PKGBUILD file not found at: $PKGBUILD_PATH" >&2
    exit 1
fi

PKGBUILD_DIR="$(cd "$(dirname "$PKGBUILD_PATH")" && pwd)"

# Auto-detect version if not specified
if [[ -z "$VERSION" ]]; then
    VERSION=$(grep -m1 '^version = ' "$PROJECT_ROOT/pyproject.toml" | cut -d'"' -f2)
    echo "Auto-detected version from pyproject.toml: $VERSION"
fi

# Auto-detect sha256 if not specified
if [[ -z "$SHA256" ]]; then
    ARCH=$(uname -m)
    EXPECTED_SUM_FILE="$PROJECT_ROOT/release/iconshift-${VERSION}-linux-${ARCH}.tar.gz.sha256"
    if [[ -f "$EXPECTED_SUM_FILE" ]]; then
        SHA256=$(awk '{print $1}' "$EXPECTED_SUM_FILE")
        echo "Auto-detected SHA-256 checksum from $EXPECTED_SUM_FILE: $SHA256"
    else
        echo "ERROR: SHA-256 not provided and checksum file not found ($EXPECTED_SUM_FILE)." >&2
        echo "Please provide --sha256 or run 'make package' first." >&2
        exit 1
    fi
fi

echo "=== Updating PKGBUILD ==="
echo "Target: $PKGBUILD_PATH"
echo "Setting pkgver=$VERSION"
echo "Setting pkgrel=1"
echo "Setting sha256sums: $SHA256"

# Update pkgver
sed -i -E "s/^[[:space:]]*pkgver=.*/pkgver=${VERSION}/" "$PKGBUILD_PATH"

# Reset pkgrel to 1 on version bump
sed -i -E "s/^[[:space:]]*pkgrel=.*/pkgrel=1/" "$PKGBUILD_PATH"

# Update sha256sums
if grep -qE "^[[:space:]]*sha256sums=" "$PKGBUILD_PATH"; then
    sed -i -E "s/^[[:space:]]*sha256sums=\([^)]*\)/sha256sums=('${SHA256}')/" "$PKGBUILD_PATH"
elif grep -qE "^[[:space:]]*sha256sums_x86_64=" "$PKGBUILD_PATH"; then
    sed -i -E "s/^[[:space:]]*sha256sums_x86_64=\([^)]*\)/sha256sums_x86_64=('${SHA256}')/" "$PKGBUILD_PATH"
fi

echo "=== Regenerating .SRCINFO ==="
(
    cd "$PKGBUILD_DIR"
    if command -v makepkg >/dev/null 2>&1; then
        makepkg --printsrcinfo > .SRCINFO
        echo ".SRCINFO regenerated successfully at $PKGBUILD_DIR/.SRCINFO"
    else
        echo "WARNING: makepkg command not available on host. Skipping .SRCINFO regeneration." >&2
    fi
)

cat << EOF

=== AUR Update Preparation Complete ===
Files updated in: $PKGBUILD_DIR
  - PKGBUILD (pkgver=${VERSION}, pkgrel=1)
  - .SRCINFO

NEXT STEPS FOR MANUAL REVIEW:
  1. cd "$PKGBUILD_DIR"
  2. git diff
  3. namcap PKGBUILD (optional QA check)
  4. git add PKGBUILD .SRCINFO
  5. git commit -m "chore(release): bump to version ${VERSION}"
  6. git push (when manually verified)
EOF
