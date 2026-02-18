"""Windows service wrapper for the TallyPrime Backup Agent.

Reads configuration from ProgramData/TallyBackupAgent/config.json and runs AgentService.
This module requires pywin32 (win32serviceutil, win32service, servicemanager) and is intended
to be packaged on Windows.
"""
from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path
from typing import Optional

try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
except Exception:  # pragma: no cover - windows only
    win32serviceutil = None
    win32service = None
    win32event = None
    servicemanager = None

from .service import AgentService
from .logging_config import setup_logging

logger = setup_logging()


def load_config() -> dict:
    pd = Path(os.environ.get("PROGRAMDATA", r"C:\\ProgramData")) / "TallyBackupAgent"
    cfgf = pd / "config.json"
    if not cfgf.exists():
        raise FileNotFoundError(f"Config not found: {cfgf}")
    return json.loads(cfgf.read_text(encoding="utf-8"))


class TallyBackupWindowsService(win32serviceutil.ServiceFramework):
    _svc_name_ = "TallyBackupAgent"
    _svc_display_name_ = "TallyPrime Backup Agent"
    _svc_description_ = "Encrypted backups of TallyPrime data to S3"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self._svc_stop = False
        self._thread: Optional[threading.Thread] = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self._svc_stop = True
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE, servicemanager.PYS_SERVICE_STARTED, (self._svc_name_, ""))
        try:
            cfg = load_config()
        except Exception as e:
            servicemanager.LogErrorMsg(f"Failed to load config: {e}")
            return

        password = cfg.get("encryption_password", "").encode()
        s3_bucket = cfg.get("s3_bucket")
        client_id = cfg.get("client_id")
        debounce = int(cfg.get("debounce_seconds", 120))
        region = cfg.get("aws_region")

        self.agent = AgentService(s3_bucket=s3_bucket, client_id=client_id, encryption_password=password, debounce_seconds=debounce, region=region)

        def run_agent():
            try:
                self.agent.start()
            except Exception as e:
                servicemanager.LogErrorMsg(f"Agent failed: {e}")

        self._thread = threading.Thread(target=run_agent, daemon=True)
        self._thread.start()

        # Wait for stop signal
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
        self.agent.stop()


if __name__ == "__main__":
    if win32serviceutil is None:
        print("pywin32 is required to run the Windows service wrapper.")
        sys.exit(1)
    win32serviceutil.HandleCommandLine(TallyBackupWindowsService)
