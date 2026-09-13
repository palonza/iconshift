#!/usr/bin/env bash
set -euo pipefail

VM_NAME="ulir-dev"
CONNECT_URI="qemu:///system"

echo "=== VM Status: $VM_NAME ==="
STATE=$(virsh -c "$CONNECT_URI" domstate "$VM_NAME" 2>/dev/null || echo "UNKNOWN")
echo "State: $STATE"

if [[ "$STATE" =~ "running" ]]; then
    IP=$(virsh -c "$CONNECT_URI" domifaddr "$VM_NAME" --source agent 2>/dev/null | awk '$3 == "ipv4" && $4 !~ /^127\./ {sub(/\/.*/, "", $4); print $4; exit}' || true)
    if [[ -z "$IP" ]]; then
        IP=$(virsh -c "$CONNECT_URI" domifaddr "$VM_NAME" 2>/dev/null | awk '$3 == "ipv4" && $4 !~ /^127\./ {sub(/\/.*/, "", $4); print $4; exit}' || true)
    fi
    if [[ -z "$IP" ]]; then
        IP=$(virsh -c "$CONNECT_URI" net-dhcp-leases default 2>/dev/null | awk '$5 ~ /^[0-9]/ && $5 !~ /^127\./ {sub(/\/.*/, "", $5); print $5; exit}' || true)
    fi
    echo "IP Address: ${IP:-Not detected yet}"
fi
