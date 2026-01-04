# Unified IPsec: Cross-Platform Data Security

> **Universal IPsec Management for Enterprise Networks**
> 
> A unified, automated, and cross-platform solution to secure data in transit across Windows, Linux, and MacOS environments.

## Overview

In modern enterprise networks, ensuring consistent encryption across diverse operating systems is a critical challenge. Different platforms utilize different tools (PowerShell, strongSwan, Racoon) and configurations, leading to operational complexity and security gaps.

**Unified IPsec** solves this by providing a **single, policy-driven** agent that runs on every node in the network. Once configured, it automatically orchestrates the native IPsec stack of the underlying operating system to enforce centrally defined security policies.

### Core Objectives
- **Unified Configuration**: One JSON/YAML policy file for all platforms.
- **Cross-Platform**: Seamless operation on Windows, Linux (Debian/RHEL), and MacOS.
- **Zero-Touch**: Automatic startup, connection management, and healing.
- **Interoperability**: Standard IKEv2/ESP tunnel negotiation.

---

## Key Features

- **🛡️ Cross-Platform Support**:
  - **Windows**: Native WFP / IPsec policy orchestration via PowerShell.
  - **Linux**: Automated `swanctl` / `strongSwan` management.
  - **MacOS**: Native integration via `strongSwan` port.
  
- **⚙️ Flexible Cryptography**:
  - **IKEv2**: AES-128/256, SHA-256/384, MODP 2048/3072.
  - **Authentication**: Pre-Shared Keys (PSK) and Certificate support (roadmap).
  
- **🚀 Performance & Reliability**:
  - **Kernel-Level Encryption**: Utilizes OS kernel stacks for minimal latency.
  - **Auto-Healing**: Monitors Security Associations (SAs) and re-negotiates if dropped.
  - **Persistent Operation**: System service integration for boot-time start.

- **📊 Observability**:
  - Unified logs across all platforms.
  - Health check API for status monitoring.

---

## Installation

### Prerequisites
- **Python**: 3.10 or higher
- **Administrator/Root Privileges**: Required to modify network policies.

### 1. Windows
**Requirements**: Windows 10/11 or Server 2016+. `PowerShell 5.1`.

```powershell
# 1. Install dependencies
pip install pywin32 pyyaml

# 2. Install as a Service
python service.py install

# 3. Start the Service
python service.py start
```

### 2. Linux (Ubuntu/Debian/RHEL)
**Requirements**: `strongSwan` (>=5.9.0) with `swanctl`.

```bash
# 1. Install strongSwan
sudo apt-get install strongswan swanctl charon-systemd

# 2. Install Python dependencies
pip install pyyaml

# 3. Run Agent (Systemd unit recommended for production)
sudo python3 -m agent.core config.json
```

### 3. MacOS
**Requirements**: `strongSwan` via Homebrew.

```bash
# 1. Install strongSwan
brew install strongswan

# 2. Install Python dependencies
pip install pyyaml

# 3. Run Agent
sudo python3 -m agent.core config.json
```

---

## Configuration

The solution uses a single `config.json` file. This file is portable across all supported operating systems.

```json
{
    "logging_level": "INFO",
    "connections": [
        {
            "name": "site-to-site",
            "mode": "tunnel",
            "ike_version": "ikev2",
            "local_subnets": ["192.168.10.0/24"],
            "remote_subnets": ["192.168.20.0/24"],
            "auth": {
                "type": "psk",
                "value": "SuperSecretKey123!"
            },
            "encryption": {
                "ike": "aes256-sha256-modp2048",
                "esp": "aes256-sha256"
            }
        }
    ]
}
```

### Parameter Reference

| Parameter | Description | Options |
|-----------|-------------|---------|
| `mode` | IPsec operation mode | `tunnel`, `transport` |
| `ike_version` | IKE Protocol Version | `ikev2` (Recommended), `ikev1` |
| `auth.type` | Authentication Method | `psk` |
| `encryption.ike` | Phase 1 Proposals | `aes256-sha256-modp2048`, `default` |
| `encryption.esp` | Phase 2 Proposals | `aes256-sha256`, `default` |

---

## Architecture

The solution follows a modular "Core-Adapter" architecture:

1.  **Agent Core**: Python-based state machine that handles configuration loading, health monitoring, and error recovery.
2.  **Platform Adapters**:
    - `agent.platforms.windows`: Calls `New-NetIPsecRule`, `New-NetIPsecPhase1AuthProposal`, etc.
    - `agent.platforms.linux`: Generates `/etc/swanctl/conf.d/agent.conf` and calls `swanctl --load-all`.
    - `agent.platforms.macos`: Adapts `swanctl` paths for MacOS environments.

---

## Development & Troubleshooting

### Building from Source
```bash
git clone https://github.com/your-repo/unified-ipsec.git
cd unified-ipsec
pip install -r requirements.txt
```

### Logs
- **Windows**: `agent.log` in the installation directory.
- **Linux/Mac**: `/var/log/syslog` or `agent.log` depending on config.

### Common Issues
- **Windows**: "Access Denied" - Ensure you are running as Administrator.
- **Linux**: "Swanctl socket not found" - Ensure the `charon` daemon is running (`systemctl start strongswan`).

---

**© 2024 Unified IPsec Team**. Built for High Performance Network Security.
