; NSIS installer script template for TallyBackupAgent
; Requires NSIS (makensis) to build.

!include "MUI2.nsh"

Name "TallyPrime Backup Agent"
OutFile "TallyBackupAgent-Installer.exe"
InstallDir "$PROGRAMFILES\\TallyBackupAgent"
SetCompressor /SOLID lzma

Page directory
Page instfiles

Section "Install"
  SetOutPath "$INSTDIR"
  File "TallyBackupAgent.exe"
  File "TallyBackupInstaller.exe"
  ; Include default config template and write to ProgramData
  File "config.json.template"

  ; Create ProgramData config folder and copy the template as config.json
  CreateDirectory "$ALLUSERSAPPDATA\\TallyBackupAgent"
  SetOutPath "$ALLUSERSAPPDATA\\TallyBackupAgent"
  ; The template was included in installer; write it to ProgramData as config.json
  FileOpen $0 "$INSTDIR\\config.json.template" r
  FileRead $0 $1
  FileClose $0
  ; Write the template contents to ProgramData\TallyBackupAgent\config.json
  FileOpen $2 "$ALLUSERSAPPDATA\\TallyBackupAgent\\config.json" w
  FileWrite $2 $1
  FileClose $2

  ; Restore output directory to ProgramFiles for rest of the install
  SetOutPath "$INSTDIR"

  ; Create shortcuts
  CreateShortCut "$DESKTOP\\TallyBackup Agent.lnk" "$INSTDIR\\TallyBackupInstaller.exe"

  ; Optionally register service via sc (requires admin)
  ExecWait 'sc create TallyBackupAgent binPath= "$INSTDIR\\TallyBackupAgent.exe" start= auto'
  ExecWait 'sc start TallyBackupAgent'
SectionEnd

Section "Uninstall"
  ExecWait 'sc stop TallyBackupAgent'
  ExecWait 'sc delete TallyBackupAgent'
  Delete "$INSTDIR\\TallyBackupAgent.exe"
  Delete "$INSTDIR\\TallyBackupInstaller.exe"
  RMDir "$INSTDIR"
  DeleteShortCut "$DESKTOP\\TallyBackup Agent.lnk"
SectionEnd
