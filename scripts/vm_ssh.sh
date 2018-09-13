#!/usr/bin/env bash
set -euo pipefail

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
    echo "ERROR: VM '$VM_NAME' is not running or has no IP. Run scripts/vm_start.sh first." >&2
    exit 1
fi

SSH_OPTS=(
    -i "$KEY_FILE"
    -o BatchMode=yes
    -o StrictHostKeyChecking=no
    -o UserKnownHostsFile=/dev/null
    -o LogLevel=ERROR
)

if [[ $# -eq 0 ]]; then
    exec ssh "${SSH_OPTS[@]}" "${USER_NAME}@${IP}"
else
    exec ssh "${SSH_OPTS[@]}" "${USER_NAME}@${IP}" "$@"
fi
