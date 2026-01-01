# Windows Unified IPsec Agent (Prototype)

A configuration-driven, headless Windows Service for orchestrating Native Windows IPsec policies.

## Features
- **Native Windows IPsec**: Uses kernel-level IPsec stack (Main Mode/Quick Mode).
- **Configuration Driven**: Single JSON/YAML config file.
- **Auto-Healing**: ISO layer that monitors SAs and refuses connections; automatically re-applies policies if broken.
- **Zero Touch**: Runs as a background service with no GUI.
- **Secure**: No secrets in logs. Memory-only PSK handling in Python.

## Requirements
- **OS**: Windows 10 / Windows 11 / Server 2016+
- **Python**: 3.10+
- **PowerShell**: 5.1+
- **Privileges**: Administrator (for Policy application)
- **Dependencies**: `pywin32` (for Service wrapper), `pyyaml` (optional, for YAML config)

## Installation

1.  **Install Python Dependencies**:
    ```powershell
    pip install pywin32 pyyaml
    ```

2.  **Configure**:
    Edit `config.json` (or create `config.yaml`).
    ```json
    {
        "mode": "tunnel",
        "auth": { "type": "psk", "value": "SecretKey" },
        "traffic": { "local_subnet": "10.0.0.0/24", "remote_subnet": "192.168.1.0/24" }
    }
    ```

3.  **Install Service**:
    Run as Administrator:
    ```powershell
    python service.py install
    ```

## Usage

- **Start Service**: `python service.py start` (or specific `sc start UnifiedIPsecAgent`)
- **Stop Service**: `python service.py stop`
- **Debug Mode**: Run standalone without service wrapper:
    ```powershell
    python agent/core.py config.json
    ```

## Verification

### Check Status
The agent logs to `agent.log`. Check for `CONNECTED`.

Manually verify IPsec SAs:
```powershell
Get-NetIPsecMainModeSA
Get-NetIPsecQuickModeSA
```
Verify Rules exist:
```powershell
Get-NetIPsecRule -Group "UnifiedIPsecAgent"
```

## Architecture

- **`agent/core.py`**: Main logic, State Machine (INIT -> APPLYING -> CONNECTED).
- **`agent/config_schema.py`**: Validation logic.
- **`scripts/*.ps1`**: PowerShell scripts for `New-NetIPsec*` calls.
- **`service.py`**: Windows Service Wrapper.

## Cleanup
To remove all policies created by this agent manually:
```powershell
powershell -File scripts/cleanup.ps1
```
Uninstall service:
```powershell
python service.py remove
```

## Limitations (Prototype)
- Only support PSK (Pre-Shared Key).
- Only supports IKEv2.
- Designed for Windows-to-Windows or Windows-to-Appliance IPsec.
