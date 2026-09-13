#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

SOURCE_BIN="$PROJECT_ROOT/dist/iconshift"
RELEASE_DIR="$PROJECT_ROOT/release"

if [[ ! -f "$SOURCE_BIN" || ! -x "$SOURCE_BIN" ]]; then
    echo "Executable not found at $SOURCE_BIN. Triggering build..."
    "$SCRIPT_DIR/build.sh"
fi

echo "=== [1/3] Detecting version and architecture ==="
VERSION=$("$SOURCE_BIN" --version 2>/dev/null | awk '{print $2}')
if [[ -z "$VERSION" ]]; then
    VERSION=$(grep -m1 '^version = ' "$PROJECT_ROOT/pyproject.toml" | cut -d'"' -f2)
fi

ARCH=$(uname -m)

if [[ -z "$VERSION" || -z "$ARCH" ]]; then
    echo "ERROR: Failed to detect version or architecture." >&2
    exit 1
fi

PACKAGE_NAME="iconshift-${VERSION}-linux-${ARCH}"
TARBALL="${PACKAGE_NAME}.tar.gz"
CHECKSUM_FILE="${TARBALL}.sha256"

mkdir -p "$RELEASE_DIR"

echo "=== [2/3] Creating distribution tarball ($TARBALL) ==="
STAGE_DIR=$(mktemp -d -t iconshift-pkg-XXXXXX)
trap 'rm -rf "$STAGE_DIR"' EXIT

mkdir -p "$STAGE_DIR/$PACKAGE_NAME"
cp "$SOURCE_BIN" "$STAGE_DIR/$PACKAGE_NAME/iconshift"
if [[ -f "$PROJECT_ROOT/README.md" ]]; then
    cp "$PROJECT_ROOT/README.md" "$STAGE_DIR/$PACKAGE_NAME/"
fi
if [[ -f "$PROJECT_ROOT/LICENSE" ]]; then
    cp "$PROJECT_ROOT/LICENSE" "$STAGE_DIR/$PACKAGE_NAME/"
fi

(
    cd "$STAGE_DIR"
    tar -czf "$RELEASE_DIR/$TARBALL" "$PACKAGE_NAME"
)

echo "=== [3/3] Calculating SHA-256 checksum ==="
(
    cd "$RELEASE_DIR"
    sha256sum "$TARBALL" > "$CHECKSUM_FILE"
)

echo "Package created successfully:"
echo "  Artifact: $RELEASE_DIR/$TARBALL"
echo "  Checksum: $RELEASE_DIR/$CHECKSUM_FILE ($(cat "$RELEASE_DIR/$CHECKSUM_FILE" | awk '{print $1}'))"
