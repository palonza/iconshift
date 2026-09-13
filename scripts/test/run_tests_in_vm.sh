#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VM_DIR="$SCRIPT_DIR/../vm"

echo "=== [1/4] Ensuring VM 'ulir-dev' is running and ready ==="
"$VM_DIR/vm_start.sh"

VM_NAME="ulir-dev"
CONNECT_URI="qemu:///system"
USER_NAME="ulir"
KEY_FILE="${HOME}/.ssh/id_rsa"

IP=$(virsh -c "$CONNECT_URI" domifaddr "$VM_NAME" --source agent 2>/dev/null | awk '$3 == "ipv4" && $4 !~ /^127\./ {sub(/\/.*/, "", $4); print $4; exit}' || true)
if [[ -z "$IP" ]]; then
    IP=$(virsh -c "$CONNECT_URI" domifaddr "$VM_NAME" 2>/dev/null | awk '$3 == "ipv4" && $4 !~ /^127\./ {sub(/\/.*/, "", $4); print $4; exit}' || true)
fi
if [[ -z "$IP" ]]; then
    IP=$(virsh -c "$CONNECT_URI" net-dhcp-leases default 2>/dev/null | awk '$5 ~ /^[0-9]/ && $5 !~ /^127\./ {sub(/\/.*/, "", $5); print $5; exit}' || true)
fi

if [[ -z "$IP" ]]; then
    echo "ERROR: Unable to resolve IP address for VM '$VM_NAME'." >&2
    exit 1
fi

SSH_CMD=(
    ssh
    -i "$KEY_FILE"
    -o BatchMode=yes
    -o StrictHostKeyChecking=no
    -o UserKnownHostsFile=/dev/null
    -o LogLevel=ERROR
    "${USER_NAME}@${IP}"
)

echo "=== [2/4] Preparing remote environment on VM ($IP) ==="
"${SSH_CMD[@]}" "rm -rf /home/ulir/builds/iconshift_v1.1 && mkdir -p /home/ulir/builds/iconshift_v1.1"

echo "=== [3/4] Synchronizing project files to VM via tar stream ==="
tar --exclude='.git' \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache' \
    --exclude='.coverage' \
    --exclude='build' \
    --exclude='dist' \
    --exclude='release' \
    -czf - -C "$PROJECT_ROOT" . | "${SSH_CMD[@]}" "tar -xzf - -C /home/ulir/builds/iconshift_v1.1"

echo "=== [4/4] Executing test suite with coverage inside VM ==="
"${SSH_CMD[@]}" 'bash -s' << 'EOF'
set -e
cd /home/ulir/builds/iconshift_v1.1

export PATH="/usr/bin:$HOME/.cargo/bin:$PATH"

echo "Running pytest with coverage inside VM using uv..."
uv run pytest --cov=src --cov-report=term-missing tests/
EOF

echo "=== Tests completed successfully inside VM ==="
