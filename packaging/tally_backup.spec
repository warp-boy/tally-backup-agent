# PyInstaller spec for TallyBackupAgent and installer GUI
# Build commands:
# py -3 -m PyInstaller --onefile --name TallyBackupAgent -p . agent/service_wrapper.py
# py -3 -m PyInstaller --onefile --name TallyBackupInstaller -p . tools/installer_gui.py

block_cipher = None

a = Analysis([
    'agent/service_wrapper.py'
], pathex=['.'], binaries=[], datas=[], hiddenimports=[], hookspath=[], runtime_hooks=[], excludes=[])
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='TallyBackupAgent', debug=False, bootloader_ignore_signals=False, strip=False, upx=True, console=False)
