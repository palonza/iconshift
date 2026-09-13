#!/usr/bin/env bash
set -euo pipefail

VM_NAME="ulir-dev"
CONNECT_URI="qemu:///system"
TIMEOUT=60

echo "Checking state of VM '$VM_NAME'..."
STATE=$(virsh -c "$CONNECT_URI" domstate "$VM_NAME" 2>/dev/null || echo "UNKNOWN")

if [[ "$STATE" != "running" ]]; then
    echo "Starting VM '$VM_NAME'..."
    virsh -c "$CONNECT_URI" start "$VM_NAME"
fi

echo "Waiting for VM to acquire IP address..."
elapsed=0
IP=""
while [[ -z "$IP" && $elapsed -lt $TIMEOUT ]]; do
    IP=$(virsh -c "$CONNECT_URI" domifaddr "$VM_NAME" --source agent 2>/dev/null | awk '$3 == "ipv4" && $4 !~ /^127\./ {sub(/\/.*/, "", $4); print $4; exit}' || true)
    if [[ -z "$IP" ]]; then
        IP=$(virsh -c "$CONNECT_URI" domifaddr "$VM_NAME" 2>/dev/null | awk '$3 == "ipv4" && $4 !~ /^127\./ {sub(/\/.*/, "", $4); print $4; exit}' || true)
    fi
    if [[ -z "$IP" ]]; then
        IP=$(virsh -c "$CONNECT_URI" net-dhcp-leases default 2>/dev/null | awk '$5 ~ /^[0-9]/ && $5 !~ /^127\./ {sub(/\/.*/, "", $5); print $5; exit}' || true)
    fi
    if [[ -n "$IP" ]]; then
        break
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done

if [[ -z "$IP" ]]; then
    echo "ERROR: Timed out waiting for VM IP address" >&2
    exit 1
fi

echo "VM '$VM_NAME' is active at $IP"

echo "Waiting for SSH service to become ready on $IP:22..."
elapsed=0
while [[ $elapsed -lt $TIMEOUT ]]; do
    if nc -z -w 2 "$IP" 22 2>/dev/null; then
        echo "SSH is ready on $IP:22"
        exit 0
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done

echo "ERROR: Timed out waiting for SSH on $IP:22" >&2
exit 1
