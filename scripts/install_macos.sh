#!/bin/bash
set -e

# Unified IPsec Agent Installer for macOS
# Requires Homebrew

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo)"
  exit 1
fi

# Detect actual user for Homebrew usage (brew shouldn't run as root often, but we need root for install)
ACTUAL_USER=$(logname || echo $SUDO_USER)
if [ -z "$ACTUAL_USER" ]; then
    echo "Could not detect actual user. Please run from a user shell with sudo."
    exit 1
fi

echo "Detecting Homebrew..."
if [ -f "/opt/homebrew/bin/brew" ]; then
    BREW_BIN="/opt/homebrew/bin/brew"
elif [ -f "/usr/local/bin/brew" ]; then
    BREW_BIN="/usr/local/bin/brew"
else
    echo "Homebrew not found. Please install Homebrew first."
    exit 1
fi

echo "Installing Dependencies (as $ACTUAL_USER)..."
sudo -u "$ACTUAL_USER" "$BREW_BIN" install strongswan python@3.10

AGENT_DIR="/opt/unified-ipsec-agent"
PLIST_DEST="/Library/LaunchDaemons/com.unified.ipsec.agent.plist"

echo "Installing Agent to $AGENT_DIR..."
mkdir -p "$AGENT_DIR"
cp -r ../agent "$AGENT_DIR/"
cp ../config.json "$AGENT_DIR/"
cp ../*.py "$AGENT_DIR/"

echo "Setting up Python Environment..."
python3 -m venv "$AGENT_DIR/venv"
"$AGENT_DIR/venv/bin/pip" install pyyaml

echo "Installing LaunchDaemon..."
cp com.unified.ipsec.agent.plist "$PLIST_DEST"
chmod 644 "$PLIST_DEST"
chown root:wheel "$PLIST_DEST"

echo "Loading Service..."
launchctl unload "$PLIST_DEST" 2>/dev/null || true
launchctl load "$PLIST_DEST"

echo "Installation Complete."
echo "Logs: /var/log/unified-ipsec-agent.log"
