import subprocess
import json
import logging
from pathlib import Path
from agent.base import IPsecBackend
from agent.config_schema import AgentConfig

class WindowsAgent(IPsecBackend):
    def __init__(self, config: AgentConfig, base_dir: Path, logger: logging.Logger):
        super().__init__(config, base_dir, logger)
        self.scripts_dir = self.base_dir / "scripts"
        self._check_admin()

    def _check_admin(self):
        try:
            import ctypes
            if ctypes.windll.shell32.IsUserAnAdmin() == 0:
                self.logger.warning("Agent is NOT running as Administrator. IPsec policy application will likely fail!")
                self.logger.warning("Please restart this terminal as Administrator.")
        except Exception as e:
            self.logger.warning(f"Could not verify Admin privileges: {e}")

    def run_powershell(self, script_name: str, args: dict = None) -> dict:
        """Executes a PowerShell script and returns parsed JSON output or success status."""
        script_path = self.scripts_dir / script_name
        if not script_path.exists():
            self.logger.error(f"Script not found: {script_path}")
            return {"status": "ERROR", "error": "Script missing"}

        # Construct command
        cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script_path)]
        if args:
            for k, v in args.items():
                cmd.append(f"-{k}")
                cmd.append(str(v))

        try:
            # self.logger.debug(f"Executing: {' '.join(cmd)}")
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60
            ) 

            if result.returncode != 0:
                self.logger.error(f"PowerShell Error ({script_name}): {result.stderr}")
                return {"status": "ERROR", "error": result.stderr.strip()}

            # Try to parse JSON from stdout if it looks like JSON
            stdout = result.stdout.strip()
            if stdout.startswith("{") and stdout.endswith("}"):
                try:
                    return json.loads(stdout)
                except json.JSONDecodeError:
                    pass 
            
            return {"status": "SUCCESS", "output": stdout}

        except subprocess.TimeoutExpired:
            self.logger.error(f"Script execution timed out: {script_name}")
            return {"status": "ERROR", "error": "Timeout"}
        except Exception as e:
            self.logger.error(f"Subprocess execution failed: {e}")
            return {"status": "ERROR", "error": str(e)}

    def apply_policy(self) -> bool:
        self.logger.info("Applying IPsec policies (Windows Native)...")
        
        # Ensure clean state by removing previous rules associated with this agent
        self.cleanup() 
        
        success_count = 0
        for conn in self.config.connections:
            self.logger.info(f"Applying connection: {conn.name}")
            
            # Windows Native usually takes single subnet string.
            # If multiple subnets provided, we might need multiple rules or complex objects.
            # For prototype, take first subnet if list provided.
            local = conn.local_subnets[0]
            remote = conn.remote_subnets[0]

            # Parse Crypto Strings to map IKEv2 parameters
            # e.g. "aes256-sha256-dh14" -> Encryption=AES256, Hash=SHA256, DHGroup=DH14
            # If parsing fails, defaults are handled by the PowerShell script parameters.
            
            ike_str = conn.encryption.ike.lower()
            enc_map = {"aes256": "AES256", "aes128": "AES128", "3des": "DES3"}
            hash_map = {"sha256": "SHA256", "sha1": "SHA1", "sha384": "SHA384"}
            dh_map = {"dh14": "DH14", "dh2": "DH2", "modp2048": "DH14"} # map modp names to windows DH
            
            w_enc = "AES256"
            w_hash = "SHA256"
            w_dh = "DH14"
            
            for k, v in enc_map.items():
                if k in ike_str: w_enc = v
            for k, v in hash_map.items():
                if k in ike_str: w_hash = v
            for k, v in dh_map.items():
                if k in ike_str: w_dh = v
                
            args = {
                "LocalSubnet": local,
                "RemoteSubnet": remote,
                "PresharedKey": conn.auth.value,
                "Mode": conn.mode.capitalize(),
                "ConnectionName": conn.name,
                "Protocol": conn.protocol.capitalize(),
                "LocalPort": conn.local_port.capitalize(),
                "RemotePort": conn.remote_port.capitalize(),
                "Encryption": w_enc,
                "Hash": w_hash,
                "DHGroup": w_dh
            }

            res = self.run_powershell("apply.ps1", args)
            
            if res.get("status") == "ERROR":
                self.logger.error(f"Failed to apply policy {conn.name}: {res.get('error')}")
            else:
                self.logger.info(f"Policy {conn.name} applied successfully.")
                success_count += 1
        
        if success_count == len(self.config.connections):
            return True
        elif success_count > 0:
            self.logger.warning("Some policies failed to apply.")
            return True # Partial success?
        else:
            return False

    def check_status(self) -> str:
        res = self.run_powershell("status.ps1", {})
        status = res.get("status", "UNKNOWN")
        if status == "ERROR":
            self.logger.warning(f"Status check failed: {res.get('error')}")
            return "DISCONNECTED" # Fail-safe
        return status

    def cleanup(self):
        self.logger.info("Cleaning up Windows policies...")
        self.run_powershell("cleanup.ps1")
