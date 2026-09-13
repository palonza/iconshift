#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

SOURCE_BIN="$PROJECT_ROOT/dist/iconshift"
INSTALL_DIR="${HOME}/.local/bin"
TARGET_BIN="$INSTALL_DIR/iconshift"

if [[ ! -f "$SOURCE_BIN" || ! -x "$SOURCE_BIN" ]]; then
    echo "ERROR: Executable binary not found at $SOURCE_BIN" >&2
    echo "Please build the project first using 'make build' or '$SCRIPT_DIR/build.sh'." >&2
    exit 1
fi

echo "Installing iconshift to $TARGET_BIN..."
install -Dm755 "$SOURCE_BIN" "$TARGET_BIN"

echo "Installation successful."
"$TARGET_BIN" --version
