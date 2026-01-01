import time
import subprocess
import logging
import os
import json
import sys
from logging.handlers import RotatingFileHandler
from enum import Enum
from pathlib import Path
from agent.config_schema import AgentConfig, load_config

# Constants
CHECK_INTERVAL = 30  # Seconds
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT = 3

class AgentState(Enum):
    INIT = "INIT"
    APPLYING = "APPLYING"
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"

class IPsecAgent:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config: AgentConfig = None
        self.state = AgentState.INIT
        self.base_dir = Path(__file__).parent.parent.resolve()
        self.scripts_dir = self.base_dir / "scripts"
        
        # Setup logging
        log_file = self.base_dir / "agent.log"
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            handlers=[
                RotatingFileHandler(log_file, maxBytes=MAX_LOG_SIZE, backupCount=LOG_BACKUP_COUNT),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger("IPsecAgent")

    def load_configuration(self):
        try:
            self.logger.info(f"Loading configuration from {self.config_path}")
            self.config = load_config(self.config_path)
            self.logger.info("Configuration loaded successfully.")
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            self.state = AgentState.ERROR
            raise

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
            ) # 60s timeout for safety check

            if result.returncode != 0:
                self.logger.error(f"PowerShell Error ({script_name}): {result.stderr}")
                return {"status": "ERROR", "error": result.stderr.strip()}

            # Try to parse JSON from stdout if it looks like JSON
            stdout = result.stdout.strip()
            if stdout.startswith("{") and stdout.endswith("}"):
                try:
                    return json.loads(stdout)
                except json.JSONDecodeError:
                    pass # Not JSON, just return text/success
            
            return {"status": "SUCCESS", "output": stdout}

        except subprocess.TimeoutExpired:
            self.logger.error(f"Script execution timed out: {script_name}")
            return {"status": "ERROR", "error": "Timeout"}
        except Exception as e:
            self.logger.error(f"Subprocess execution failed: {e}")
            return {"status": "ERROR", "error": str(e)}

    def check_status(self) -> str:
        """Checks actual IPsec status via PowerShell."""
        # args = {"RemoteSubnet": self.config.traffic.remote_subnet} # Optional filtering
        res = self.run_powershell("status.ps1", {})
        
        status = res.get("status", "UNKNOWN")
        if status == "ERROR":
            self.logger.warning(f"Status check failed: {res.get('error')}")
            # If status check fails, we might assume DISCONNECTED or stay in current state?
            # Safer to assume DISCONNECTED to trigger re-apply if it persists.
            return AgentState.DISCONNECTED.value
        
        return status # CONNECTED or DISCONNECTED

    def apply_policy(self):
        """Applies configuration via PowerShell."""
        self.state = AgentState.APPLYING
        self.logger.info("Applying IPsec policy...")

        # Arguments mapping
        args = {
            "LocalSubnet": self.config.traffic.local_subnet,
            "RemoteSubnet": self.config.traffic.remote_subnet,
            "PresharedKey": self.config.auth.value,
            "Mode": self.config.mode.capitalize() # Tunnel or Transport
        }

        res = self.run_powershell("apply.ps1", args)
        
        if res.get("status") == "ERROR":
            self.logger.error(f"Failed to apply policy: {res.get('error')}")
            self.state = AgentState.ERROR
        else:
            self.logger.info("Policy application reported success.")
            # Verify immediately? Or let next loop handle it?
            # Let's verify immediately to transition fast.
            status = self.check_status()
            if status == "CONNECTED":
                self.state = AgentState.CONNECTED
                self.logger.info("Link is UP (Verified).")
            else:
                self.logger.warning("Policy applied but link is not yet CONNECTED. Waiting for negotiation...")
                # It might take a moment to negotiate main mode. Start loop.
                self.state = AgentState.DISCONNECTED

    def cleanup(self):
        self.logger.info("Cleaning up policies...")
        self.run_powershell("cleanup.ps1")

    def run(self):
        self.logger.info("Agent starting...")
        try:
            self.load_configuration()
        except:
            return # Exit if config fails

        # Initial cleanup to ensure clean slate?
        # Maybe safer to just try Applying. 
        # But if we want deterministic prototype: Apply on start.
        self.apply_policy()

        while True:
            try:
                current_status = self.check_status()
                
                if current_status == "CONNECTED":
                    if self.state != AgentState.CONNECTED:
                        self.logger.info("State transition: -> CONNECTED")
                        self.state = AgentState.CONNECTED
                    # Heartbeat log every once in a while?
                    # self.logger.debug("Heartbeat: Connected")

                elif current_status == "DISCONNECTED":
                    if self.state == AgentState.CONNECTED:
                        self.logger.warning("Lost connection! State transition: -> DISCONNECTED")
                    
                    self.logger.info("Link is DOWN. Re-applying policy...")
                    self.state = AgentState.DISCONNECTED
                    self.cleanup() # Clean before re-apply to be safe
                    self.apply_policy()

                # Sleep
                time.sleep(CHECK_INTERVAL)

            except KeyboardInterrupt:
                self.logger.info("Agent stopping (User Interrupt)...")
                self.cleanup()
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in main loop: {e}")
                self.state = AgentState.ERROR
                time.sleep(CHECK_INTERVAL) # Wait before retry

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python core.py <config_path>")
        sys.exit(1)
    
    config_path = sys.argv[1]
    agent = IPsecAgent(config_path)
    agent.run()
