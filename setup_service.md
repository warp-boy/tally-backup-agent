Windows Service & PyInstaller Instructions
========================================

1) Install pywin32 and pyinstaller in your Windows Python environment

```powershell
py -3 -m pip install -r requirements.txt
py -3 -m pip install pyinstaller
```

2) Bundle into an EXE (example)

```powershell
py -3 -m PyInstaller --onefile --name TallyBackupAgent -p . agent/main.py
```

3) Create a Windows Service wrapper

You should implement a small `service_wrapper.py` that calls `agent.service.run_console` when run as a console, and implements `win32serviceutil.ServiceFramework` for service mode. The `agent/service.py` already includes `AgentService` which you can call from the wrapper.

4) Register service using `sc create` or `pywin32` helper

Example using `sc`:

```powershell
sc create TallyBackupAgent binPath= "C:\\path\\to\\TallyBackupAgent.exe" start= auto
sc description TallyBackupAgent "TallyPrime encrypted backup agent"
sc start TallyBackupAgent
```

Notes
- Run the service using a domain/local user with access to the Tally Data folder if that folder is on a network share.
- For enterprise deployments, prefer storing secrets in AWS KMS/Secrets Manager and call KMS to decrypt the data key at runtime.

Additional packaging options
---------------------------
- Use `PyInstaller` to produce a single EXE for the service wrapper and another EXE for the installer GUI. Example build commands:

```powershell
py -3 -m pip install pyinstaller
py -3 -m PyInstaller --onefile --name TallyBackupAgent agent/service_wrapper.py
py -3 -m PyInstaller --onefile --name TallyBackupInstaller tools/installer_gui.py
```

- Use NSIS to create an installer that bundles both EXEs and registers the service. Example NSIS template is in `packaging/install.nsi`.

- The `tools/installer_gui.py` writes configuration to `%PROGRAMDATA%\\TallyBackupAgent\\config.json`. The service wrapper reads that file at startup.
