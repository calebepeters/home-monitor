#!/usr/bin/env bash
# ABOUTME: Install script for Ubuntu 24.04 — sets up the network monitor as a systemd service
# ABOUTME: Run as root; installs deps, creates venv, grants ICMP capability, enables service

set -euo pipefail

INSTALL_DIR="/opt/network-monitor"

echo "==> Updating packages and installing dependencies..."
apt-get update && apt-get install -y python3-pip python3-venv git

echo "==> Creating virtual environment at ${INSTALL_DIR}/venv..."
mkdir -p "${INSTALL_DIR}"
python3 -m venv "${INSTALL_DIR}/venv"

echo "==> Installing Python dependencies..."
"${INSTALL_DIR}/venv/bin/pip" install --upgrade pip
"${INSTALL_DIR}/venv/bin/pip" install -r "${INSTALL_DIR}/requirements.txt"

echo "==> Setting cap_net_raw on Python binary for unprivileged ICMP ping..."
setcap cap_net_raw+ep "${INSTALL_DIR}/venv/bin/python3"

echo "==> Installing systemd service..."
cp "${INSTALL_DIR}/monitor.service" /etc/systemd/system/monitor.service

echo "==> Enabling and starting service..."
systemctl daemon-reload
systemctl enable monitor
systemctl start monitor

HOSTNAME=$(hostname -I | awk '{print $1}')
echo ""
echo "Setup complete. Dashboard at http://${HOSTNAME}:8080"
