#!/bin/bash
set -e

# Unified IPsec Agent Installer for Linux
# Supports Debian/Ubuntu and RHEL/CentOS

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Detecting OS..."
if [ -f /etc/debian_version ]; then
    OS="Debian"
    echo "Detected Debian/Ubuntu"
    apt-get update
    apt-get install -y strongswan strongswan-pki swanctl python3 python3-venv python3-pip
elif [ -f /etc/redhat-release ]; then
    OS="RHEL"
    echo "Detected RHEL/CentOS"
    yum install -y strongswan strongswan-pki swanctl python3 python3-venv
else
    echo "Unsupported OS"
    exit 1
fi

AGENT_DIR="/opt/unified-ipsec-agent"
SERVICE_FILE="/etc/systemd/system/unified-ipsec-agent.service"

echo "Installing Agent to $AGENT_DIR..."
mkdir -p "$AGENT_DIR"
cp -r ../agent "$AGENT_DIR/"
cp ../config.json "$AGENT_DIR/"
cp ../*.py "$AGENT_DIR/"

echo "Setting up Python Environment..."
python3 -m venv "$AGENT_DIR/venv"
"$AGENT_DIR/venv/bin/pip" install pyyaml

echo "Creating Systemd Service..."
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Unified Cross-Platform IPsec Agent
After=network.target strongswan.service

[Service]
Type=simple
User=root
WorkingDirectory=$AGENT_DIR
ExecStart=$AGENT_DIR/venv/bin/python -m agent.core config.json
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable unified-ipsec-agent
systemctl start unified-ipsec-agent

echo "Installation Complete. Agent is running."
echo "Logs: journalctl -u unified-ipsec-agent -f"
