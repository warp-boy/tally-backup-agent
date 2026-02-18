TallyPrime Backup Agent
======================

Overview
--------
Production-grade Windows backup agent for TallyPrime. Detects Tally installation, reads `tally.ini` to find Data path, validates, monitors files with debounce logic, creates safe encrypted backups and uploads to AWS S3 using multipart uploads.

Key Features
- Tally detection via registry and common paths
- Config reader for `tally.ini` (Data path extraction)
- Validation of data directory and company folders
- Watchdog-based monitoring with debounce (configurable)
- Safe copy -> compress -> AES-256-GCM encryption
- S3 multipart uploads with retry/exponential backoff
- Rotating logs and graceful shutdown

Installation
------------
1. Create a Python 3.11+ virtualenv and install requirements:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Configure AWS credentials (recommended via environment or IAM role on EC2).

Usage (development / debug)
---------------------------
Run locally (console):

```bash
python -m agent.main --bucket your-bucket --client-id client123 --password 'supersecret'
```

Building Windows EXEs with Wine
--------------------------------
If you don't have a Windows build agent you can use Wine to produce Windows EXEs on macOS/Linux. Results vary; testing on a real Windows VM is recommended.

1. Ensure `wine`, `curl` and `unzip` are installed on your machine.
2. Run the helper script from repository root (it will download a Windows Python installer unless you provide one):

```bash
./packaging/build_with_wine.sh --out ./release
```

3. The script will:
- Install Windows Python under a Wine prefix
- Install required Python packages and `pyinstaller`
- Build `TallyBackupAgent.exe` and `TallyBackupInstaller.exe` via PyInstaller
- Install NSIS under Wine and run `makensis` to create the final installer

4. Check `./release` for produced EXEs and the NSIS installer. Test on a clean Windows VM.

Notes:
- Some dependencies (native wheels) may require additional runtime libraries inside Wine. If builds fail, prefer using the GitHub Actions Windows workflow in `.github/workflows/build-windows.yml`.
- Code-signing is not performed by the Wine script; use the GitHub Actions signing step or sign the EXEs on a Windows machine with `signtool.exe`.

Production & Windows Service
---------------------------
See `setup_service.md` for guidance to convert into a Windows EXE using PyInstaller and register as a Windows Service (pywin32). Always run the service as a service account with least privilege.

Security notes
--------------
- Prefer storing encryption keys in secure secrets stores (AWS KMS, Secrets Manager) rather than plaintext in environment variables.
- The agent derives an AES-256 key from the provided password using PBKDF2-HMAC-SHA256 with a per-file salt.
- No plaintext backups are stored; only encrypted files are kept.

Project layout
--------------
agent/
  detector.py
  config_reader.py
  validator.py
  watcher.py
  backup_engine.py
  encryption.py
  uploader.py
  service.py
  main.py
  logging_config.py

Support & Extensibility
-----------------------
The code is modular to allow adding other ERP systems in the future. Replace detection/config modules to support new products.
