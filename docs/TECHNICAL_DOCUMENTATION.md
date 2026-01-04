# Unified Cross-Platform IPsec Solution: Technical Documentation

## 1. Executive Summary
The Unified Cross-Platform IPsec Solution is a software agent designed to orchestrate secure, encrypted communication channels across heterogeneous network environments. By abstracting the complexities of operating-system-specific IPsec implementations (such as Windows Filtering Platform on Windows and StrongSwan/XFRM on Linux), the solution provides a single control plane for network administrators. This document details the technical architecture, design decisions, and operational manual for the solution.

## 2. Technical Architecture

The system is built on a **Controller-Adapter Pattern**, decoupling the business logic of policy management from the low-level execution of cryptographic parameters.

### 2.1 High-Level Components

*   **Policy Engine (Core)**: Written in Python 3.10+, this module is responsible for parsing configuration, validating schema integrity, and maintaining the lifecycle state of the agent (INIT, APPLYING, CONNECTED, ERROR).
*   **Platform Abstraction Layer (PAL)**: A set of interface-compliant drivers that translate abstract security intent (e.g., "Encrypt traffic to 10.0.0.2") into OS-specific commands.
*   **Health Monitor**: A background thread that continuously polls the kernel status of established Security Associations (SAs) and triggers auto-healing routines if anomalies are detected.

### 2.2 Platform Implementations

#### Windows Architecture
On Windows, the agent interacts directly with the **Windows Filtering Platform (WFP)** via the `NetSecurity` PowerShell module.
*   **Mechanism**: The agent spawns a tailored PowerShell session.
*   **Commands**: Utilizes `New-NetIPsecMainModeRule` for IKEv1/v2 Phase 1 negotiation and `New-NetIPsecQuickModeRule` for Phase 2 traffic protection.
*   **Persistence**: Policies are applied to the "Persistent Store" to survive reboots, although the agent re-verifies them at startup.

#### Linux & MacOS Architecture
On Unix-like systems, the agent leverages **strongSwan** as the IKE daemon, specifically utilizing the **vici** interface via the `swanctl` command-line tool.
*   **Mechanism**: The agent generates a structured `swanctl.conf` file in `/etc/swanctl/conf.d/`.
*   **commands**: Executes `swanctl --load-all` to atomically swap configurations and `swanctl --initiate` to trigger tunnels.
*   **Kernel Integration**: StrongSwan communicates with the Linux kernel via the XFRM (Transform) interface to install encryption policies.

---

## 3. Code Structure Description

The source code is organized to promote modularity and testability.

```text
/
├── agent/
│   ├── core.py           # Main entry point and event loop
│   ├── config_schema.py  # Data models and validation logic
│   └── platforms/        # OS-specific implementation files
│       ├── windows.py    # WFP/PowerShell implementation
│       ├── linux.py      # StrongSwan/Swanctl implementation
│       └── macos.py      # MacOS StrongSwan adaptation
├── scripts/              # Helper scripts (installers, cleanup)
├── service.py            # Windows Service wrapper logic
└── config.json           # Centralized configuration file
```

### Key Classes
*   **`IPsecAgent` (`agent/core.py`)**: The singleton controller. It initializes the backend, starts the health API (port 8080 default), and runs the main keep-alive loop.
*   **`AgentConfig` (`agent/config_schema.py`)**: A Pydantic-style data class that ensures type safety for IP addresses, subnets, and cryptographic parameters before they reach the OS layer.
*   **`WindowsAgent` / `LinuxAgent`**: Concrete implementations of the `IPsecBackend` abstract base class.

---

## 4. Installation Procedure

### 4.1 System Dependencies
*   **Windows**: Setup requires the `pywin32` library to interface with the Windows Service Control Manager.
*   **Linux**: Requires `strongswan`, `strongswan-swanctl`, and `charon-systemd`.
*   **MacOS**: Requires `strongswan` installed via Homebrew.

### 4.2 Deployment Steps

1.  **Prepare the Environment**:
    Ensure Python 3.10+ is installed and added to the system PATH.
    
2.  **Define Policy**:
    Modify `config.json` to define the Local/Remote subnets and Pre-Shared Key (PSK).
    
    ```json
    "connections": [{
        "local_subnets": ["10.1.0.0/16"],
        "remote_subnets": ["10.2.0.0/16"],
        "auth": { "type": "psk", "value": "StrongKey123" }
    }]
    ```

3.  **Install Service**:
    *   **Windows**: `python service.py install`
    *   **Linux**: Copy `scripts/unified-ipsec.service` to `/etc/systemd/system/` and enable it.

4.  **Verification**:
    Tail the logs: `tail -f agent.log` (Linux) or check event viewer (Windows). The log should show `[INFO] Policy applied successfully.`

---

## 5. Security Model & Considerations

### 5.1 Cryptography
The solution enforces **Suite B** compatible algorithms by default but remains configurable for legacy support.
*   **Encryption**: AES-GCM (128/256) is preferred for performance on modern CPUs with AES-NI instructions.
*   **Integrity**: SHA-256 or higher.
*   **Diffie-Hellman**: Modp2048 (Group 14) is the minimum default.

### 5.2 Key Management
Currently, the solution utilizes **Pre-Shared Keys (PSK)**. Keys are read from the protected configuration file and injected directly into the IKE daemon's memory.
*   *Future Scope*: Certificate-based authentication (PKI) using X.509 certificates is planned for V2.

### 5.3 Network Traversal
The solution includes support for **NAT-Traversal (NAT-T)**, encapsulating ESP packets in UDP port 4500 if a NAT device is detected between the endpoints.

---

## 6. Challenges & Solutions

### 6.1 State Synchronization
*   *Challenge*: Windows IPsec policies can be complex to verify programmatically compared to `swanctl --list-sas`.
*   *Solution*: The Windows agent implements a double-check mechanism, querying both the `NetIPsecRule` (policy existence) and `NetIPsecQuickModeSA` (active tunnel) to determine true connectivity status.

### 6.2 Latency Minimization
*   *Challenge*: User-space encryption introduces significant overhead.
*   *Solution*: By strictly orchestrating **Kernel-Mode IPSec** (Native WFP on Windows, XFRM on Linux), packet processing remains in the kernel, ensuring near-line-rate performance limited only by CPU AES capabilities.

---

## 7. Future Enhancements
1.  **Central Management Dashboard**: A web-based UI to push changes to `config.json` remotely.
2.  **Telemetry Reporting**: Sending packet loss and jitter stats to a central collector (e.g., Prometheus).
3.  **Mesh VPN**: Automated full-mesh configuration for multi-site deployments.
