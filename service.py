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

from agent.core import IPsecAgent

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
            # We can't easily interrupt the agent loop nicely if it's sleeping,
            # but the service restart logic will kill eventually.
            # In a real app we'd signal the agent.
            # agent.py doesn't have a check for external stop signal other than KeyboardInterrupt (which is main thread-ish).
            # We rely on process termination or improved signaling.
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
            # Note: agent.run() matches a while loop. We need to adapt it to check stop_event.
            # We will override the run loop here or modify Agent to accept a stop callback?
            # Easiest: modifying Agent to respect a stop flag is cleaner. 
            # But since we can't easily change the Agent class now without re-writing, 
            # let's run the Agent's logic step-by-step or just wrapping it?
            # Actually, `agent.run()` loops forever.
            # We should probably run the agent in a thread or modified loop.
            # Let's use a simple approach: The Service triggers the agent steps.
            
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
                        if self.agent.state != "CONNECTED": # Using string comparison or Enum? Enum.
                             # Need to access Enum from agent
                             # self.agent.state is an Enum.
                             pass # Logging is handled inside agent helper if we used it, but we are external now.
                             # Actually agent.run() handles logic nicely.
                             # If we call `agent.check_status()` and `agent.apply_policy()`, we duplicate logic.
                             # Better: Modify agent to be serviceable? 
                             # Or just run the check every N seconds using WaitForSingleObject timeout.
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
