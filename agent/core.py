import time
import subprocess
import logging
import os
import json
import sys
import platform
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
        self.backend = None
        self.logger = None
        
        # Initialize basic logging immediately
        self.setup_logging()

    def setup_logging(self):
        log_level = logging.INFO
        if self.config and self.config.logging_level.lower() == "debug":
            log_level = logging.DEBUG
        
        handlers = []
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s] %(message)s")

        # Config-based logging
        log_type = self.config.logging_type if self.config else "file"
        
        if log_type == "syslog":
            if platform.system() != "Windows":
                 from logging.handlers import SysLogHandler
                 # Try /dev/log for Linux/Mac
                 address = "/dev/log" if os.path.exists("/dev/log") else ("/var/run/syslog" if os.path.exists("/var/run/syslog") else ('localhost', 514))
                 sh = SysLogHandler(address=address)
                 sh.setFormatter(logging.Formatter('%(name)s: %(message)s'))
                 handlers.append(sh)
            else:
                 # Windows doesn't generally Support SysLogHandler local socket easily without config
                 # Fallback to file for Windows
                 print("Syslog not supported natively on Windows via Python defaults. Falling back to file.")
                 log_type = "file"

        if log_type == "file":
            log_file = self.base_dir / "agent.log"
            fh = RotatingFileHandler(log_file, maxBytes=MAX_LOG_SIZE, backupCount=LOG_BACKUP_COUNT)
            fh.setFormatter(formatter)
            handlers.append(fh)
        
        # Always log to stdout for container/systemd visibility unless explicitly disabled
        if log_type == "stdout" or log_type == "file":
             sh = logging.StreamHandler(sys.stdout)
             sh.setFormatter(formatter)
             handlers.append(sh)

        # Clear existing handlers if re-initializing
        root_logger = logging.getLogger()
        if root_logger.handlers:
            for h in root_logger.handlers[:]:
                 root_logger.removeHandler(h)
        
        logging.basicConfig(level=log_level, handlers=handlers, force=True)
        self.logger = logging.getLogger("IPsecAgent")

    def start_health_api(self):
        if not self.config or not self.config.api_port:
            return

        import http.server
        import threading
        
        agent_ref = self

        class HealthHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/status":
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    
                    status = agent_ref.check_status()
                    current_state = agent_ref.state.value
                    
                    resp = {
                        "status": status,
                        "agent_state": current_state,
                        "uptime": "TODO" # Could add uptime
                    }
                    self.wfile.write(json.dumps(resp).encode())
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args):
                return # Silence console spam

        def run_server():
            server_address = ('', self.config.api_port)
            try:
                httpd = http.server.HTTPServer(server_address, HealthHandler)
                print(f"Health API running on port {self.config.api_port}")
                httpd.serve_forever()
            except Exception as e:
                print(f"Failed to start API server: {e}")

        t = threading.Thread(target=run_server, daemon=True)
        t.start()

    def load_configuration(self):
        try:
            # Need basic logger first to log loading
            if not self.logger: self.setup_logging() 
            
            self.logger.info(f"Loading configuration from {self.config_path}")
            self.config = load_config(self.config_path)
            
            # Re-setup logging with config
            self.setup_logging()
            self.logger.info("Configuration loaded successfully.")
            
            self._init_backend()
            self.start_health_api()
        except Exception as e:
            if self.logger: self.logger.error(f"Failed to load configuration: {e}")
            else: print(f"Failed to load configuration: {e}")
            self.state = AgentState.ERROR
            raise

    def _init_backend(self):
        system = platform.system()
        self.logger.info(f"Detected OS: {system}")
        
        if system == "Windows":
            from agent.platforms.windows import WindowsAgent
            self.backend = WindowsAgent(self.config, self.base_dir, self.logger)
        elif system == "Linux":
            from agent.platforms.linux import LinuxAgent
            self.backend = LinuxAgent(self.config, self.base_dir, self.logger)
        elif system == "Darwin":
            from agent.platforms.macos import MacOSAgent
            self.backend = MacOSAgent(self.config, self.base_dir, self.logger)
        else:
            raise NotImplementedError(f"Unsupported OS: {system}")

    def check_status(self) -> str:
        if not self.backend: return AgentState.ERROR.value
        return self.backend.check_status()

    def apply_policy(self):
        if not self.backend: return
        self.state = AgentState.APPLYING
        if self.backend.apply_policy():
             # Verify immediately
            status = self.check_status()
            if status == "CONNECTED":
                self.state = AgentState.CONNECTED
                self.logger.info("Link is UP (Verified).")
            else:
                self.logger.warning("Policy applied but link is not yet CONNECTED. Waiting for negotiation...")
                self.state = AgentState.DISCONNECTED
        else:
            self.state = AgentState.ERROR

    def cleanup(self):
        if self.backend:
            self.backend.cleanup()

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
