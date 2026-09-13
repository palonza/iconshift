#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

BUILD_DIR="$PROJECT_ROOT/build/pyinstaller"
DIST_DIR="$PROJECT_ROOT/dist"
TARGET_BIN="$DIST_DIR/iconshift"
ENTRYPOINT="$PROJECT_ROOT/packaging/entrypoint.py"

echo "=== [1/4] Cleaning previous build artifacts ==="
rm -rf "$BUILD_DIR" "$TARGET_BIN" "$PROJECT_ROOT/iconshift.spec"
mkdir -p "$DIST_DIR"

echo "=== [2/4] Building standalone Linux executable with PyInstaller via uv ==="
(
    cd "$PROJECT_ROOT"
    uv run --with pyinstaller pyinstaller \
        --noconfirm \
        --clean \
        --onefile \
        --name iconshift \
        --paths "$PROJECT_ROOT/src" \
        --workpath "$BUILD_DIR" \
        --distpath "$DIST_DIR" \
        --specpath "$PROJECT_ROOT/build" \
        "$ENTRYPOINT"
)

echo "=== [3/4] Validating generated binary ==="
if [[ ! -f "$TARGET_BIN" ]]; then
    echo "ERROR: Expected binary not found at $TARGET_BIN" >&2
    exit 1
fi

if [[ ! -x "$TARGET_BIN" ]]; then
    echo "ERROR: Generated binary at $TARGET_BIN is not executable" >&2
    exit 1
fi

echo "Binary built successfully at: $TARGET_BIN"

echo "=== [4/4] Running functional sanity checks ==="
"$TARGET_BIN" --version
"$TARGET_BIN" --help >/dev/null

echo "Build check passed."
