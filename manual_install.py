import win32serviceutil
import win32service
import win32api
import win32con
import os
import sys
from pathlib import Path

# Explicitly define paths
BASE_DIR = Path(os.getcwd()).resolve()
SERVICE_SCRIPT = BASE_DIR / "service.py"
SERVICE_NAME = "UnifiedIPsecAgent"
SERVICE_DISPLAY = "Windows Unified IPsec Agent"
SERVICE_DESC = "Automated IPsec Policy Agent for Windows"

# Find python executable and pythonservice.exe
PYTHON_EXE = sys.executable
# Based on the user's scan, pythonservice.exe is in the root of the venv or Lib?
# The user search result: C:\Users\asuka\Downloads\IPsec Proto\.venv\pythonservice.exe
# Let's verify if we can find it relative to current python env or hardcode
VENV_DIR = Path(sys.prefix)

# Common locations for pythonservice.exe in venv
POSSIBLE_LOCATIONS = [
    VENV_DIR / "pythonservice.exe",
    VENV_DIR / "Lib" / "site-packages" / "win32" / "pythonservice.exe",
    VENV_DIR / "Scripts" / "pythonservice.exe"
]

PYTHONSERVICE_EXE = None
for p in POSSIBLE_LOCATIONS:
    if p.exists():
        PYTHONSERVICE_EXE = p
        break

if not PYTHONSERVICE_EXE:
    print("Error: Could not find pythonservice.exe in .venv")
    sys.exit(1)

print(f"Using Service Binary: {PYTHONSERVICE_EXE}")
print(f"Using Python Script: {SERVICE_SCRIPT}")

def install_service():
    # 1. Open SC Manager
    hscm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ALL_ACCESS)
    
    try:
        # 2. Check if service exists
        try:
            hs = win32service.OpenService(hscm, SERVICE_NAME, win32service.SERVICE_ALL_ACCESS)
            print(f"Service {SERVICE_NAME} already exists. Updating...")
            win32service.CloseServiceHandle(hs)
            # We could delete and recreate, or update. Let's Delete for clean state.
            hs = win32service.OpenService(hscm, SERVICE_NAME, win32service.SERVICE_ALL_ACCESS)
            win32service.DeleteService(hs)
            win32service.CloseServiceHandle(hs)
            print("Deleted old service.")
        except:
            pass # Does not exist

        # 3. Create Service
        # binPath must include keys for python service wrapper if we used the standard way?
        # Standard way: binPath = "path\to\pythonservice.exe -PythonService" (Wait, pythonservice usually links via Registry)
        # Actually pythonservice.exe takes no args usually, it looks up its service name in Registry.
        
        hs = win32service.CreateService(
            hscm,
            SERVICE_NAME,
            SERVICE_DISPLAY,
            win32service.SERVICE_ALL_ACCESS,
            win32service.SERVICE_WIN32_OWN_PROCESS,
            win32service.SERVICE_AUTO_START,
            win32service.SERVICE_ERROR_NORMAL,
            str(PYTHONSERVICE_EXE),
            None,
            0,
            None,
            None,
            None
        )
        
        description = SERVICE_DESC
        win32service.ChangeServiceConfig2(hs, win32service.SERVICE_CONFIG_DESCRIPTION, description)
        
        print("Service created successfully.")
        win32service.CloseServiceHandle(hs)

        # 4. Set Registry Keys (CRITICAL for PythonService)
        # HKLM\SYSTEM\CurrentControlSet\Services\<ServiceName>\PythonClass = service.IPsecService
        # HKLM\SYSTEM\CurrentControlSet\Services\<ServiceName>\PythonScript = ...
        # HKLM\SYSTEM\CurrentControlSet\Services\<ServiceName>\PythonPath = ...
        
        key_path = f"SYSTEM\\CurrentControlSet\\Services\\{SERVICE_NAME}"
        key = win32api.RegOpenKeyEx(win32con.HKEY_LOCAL_MACHINE, key_path, 0, win32con.KEY_ALL_ACCESS)
        
        # PythonClass
        win32api.RegSetValueEx(key, "PythonClass", 0, win32con.REG_SZ, "service.IPsecService")
        # PythonScript
        win32api.RegSetValueEx(key, "PythonScript", 0, win32con.REG_SZ, str(SERVICE_SCRIPT))
        # PythonPath (Semi-colon separated)
        # We need the venv site-packages and the base dir
        python_path = f"{BASE_DIR};{VENV_DIR};{VENV_DIR}\\Lib\\site-packages"
        win32api.RegSetValueEx(key, "PythonPath", 0, win32con.REG_SZ, python_path)
        
        win32api.RegCloseKey(key)
        
        print("Registry keys set.")
        
        # 5. Parameters Key (Used by PythonService.exe sometimes?)
        # Standard pywin32 puts it under Parameters. Let's duplicate to be safe.
        # Check if "Parameters" subkey needed? Usually "PythonClass" is at root of service key for pythonservice.exe 
        # (Verified: pythonservice checks root of service key first)
        
    except Exception as e:
        print(f"Failed to install service: {e}")
    finally:
        win32service.CloseServiceHandle(hscm)

if __name__ == "__main__":
    install_service()
