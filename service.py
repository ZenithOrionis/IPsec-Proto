import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os
from pathlib import Path

# Add current directory to path so we can import agent modules
# Service runs in different CWD usually (System32), so we need absolute paths.
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

from agent.core import IPsecAgent, AgentState

class IPsecService(win32serviceutil.ServiceFramework):
    _svc_name_ = "UnifiedIPsecAgent"
    _svc_display_name_ = "Windows Unified IPsec Agent"
    _svc_description_ = "Automated IPsec Policy Agent for Windows"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.running = False
        self.agent = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        self.running = False
        if self.agent:
            pass

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.running = True
        
        # Determine config path
        # Assume config.json in the same dir as the service script/exe
        config_path = BASE_DIR / "config.json"
        
        try:
            self.agent = IPsecAgent(str(config_path))
            
            # Run the agent logic.
            self.agent.load_configuration()
            self.agent.apply_policy()
            
            while self.running:
                # check stop event
                rc = win32event.WaitForSingleObject(self.stop_event, 1000) # 1s wait
                if rc == win32event.WAIT_OBJECT_0:
                    break
                    
                # Run Agent Monitor Logic
                # We replicate agent.run loop logic here to control the sleep/exit
                try:
                    current_status = self.agent.check_status()
                    
                    if current_status == "CONNECTED":
                        if self.agent.state != AgentState.CONNECTED:
                            # State transition logging handled by agent logic if driven by agent.run()
                            # Here we are manually checking.
                            pass
                    
                    if current_status == "DISCONNECTED":
                         # Re-apply
                         self.agent.cleanup() # self.agent.cleanup() uses PS
                         self.agent.apply_policy()
                    
                    # We wait N seconds total (CHECK_INTERVAL), but checking stop_event frequently?
                    # Let's wait 30 * 1s
                    for _ in range(30):
                         if win32event.WaitForSingleObject(self.stop_event, 1000) == win32event.WAIT_OBJECT_0:
                             self.running = False
                             break
                except Exception as e:
                    # Log error to service log
                    servicemanager.LogInfoMsg(f"Agent Loop Error: {e}")
            
            self.agent.cleanup()
            
        except Exception as e:
            servicemanager.LogErrorMsg(f"Service Fatal Error: {e}")
            
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(IPsecService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(IPsecService)
