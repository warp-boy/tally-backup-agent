<#
Build script for Windows installer (run on Windows build machine).

Prerequisites:
- Python 3.8+ with dependencies installed (pip install -r requirements.txt pyinstaller)
- PyInstaller on PATH
- NSIS (makensis) on PATH

Usage:
.
  .\build_installer.ps1 -Version 1.0.0 -OutputDir .\release

#>

param(
    [string]$Version = "0.1.0",
    [string]$OutputDir = ".\release",
    [string]$IconPath = "",
    [switch]$NoClean
)

Set-StrictMode -Version Latest

function Ensure-Tool {
    param($name)
    $which = Get-Command $name -ErrorAction SilentlyContinue
    if (-not $which) {
        Write-Error "$name not found on PATH. Please install it and retry."
        exit 1
    }
}

function Resolve-Makensis {
    $exe = Get-Command makensis -ErrorAction SilentlyContinue
    if ($exe) { return $exe.Path }

    $candidates = @(
        "C:\\Program Files (x86)\\NSIS\\makensis.exe",
        "C:\\Program Files\\NSIS\\makensis.exe",
        "C:\\ProgramData\\chocolatey\\lib\\nsis\\tools\\makensis.exe"
    )

    foreach ($cand in $candidates) {
        if (Test-Path $cand) { return $cand }
    }

    return $null
}

Ensure-Tool pyinstaller
$makensisPath = Resolve-Makensis
if (-not $makensisPath) {
    Write-Error "makensis not found on PATH or in common install locations. Please install NSIS or add makensis to PATH."
    exit 1
}
Write-Host "Using makensis: $makensisPath"
Set-Variable -Name MakensisExe -Value $makensisPath -Scope Script

$ProjectRoot = Resolve-Path "..\.." -Relative | Split-Path -Parent
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$RepoRoot = Resolve-Path "$ScriptDir\..\..\" -ErrorAction SilentlyContinue
if (-not $RepoRoot) { $RepoRoot = Get-Location }

$distDir = Join-Path $RepoRoot $OutputDir
if (-not (Test-Path $distDir)) { New-Item -ItemType Directory -Path $distDir | Out-Null }

Write-Host "Building service EXE (service_wrapper)..."
$svcSpec = "agent/service_wrapper.py"
$svcName = "TallyBackupAgent"
$svcArgs = "--noconsole --clean"

$pyInstSvcArgs = "--onefile --name $svcName $svcSpec $svcArgs"
if ($IconPath) { $pyInstSvcArgs += " --icon $IconPath" }

pyinstaller $pyInstSvcArgs
if ($LASTEXITCODE -ne 0) { Write-Error "PyInstaller failed for service"; exit 1 }

Write-Host "Building installer GUI EXE (installer_gui)..."
$instSpec = "tools/installer_gui.py"
$instName = "TallyBackupInstaller"
$pyInstInstArgs = "--onefile --name $instName $instSpec --noconsole"
if ($IconPath) { $pyInstInstArgs += " --icon $IconPath" }

pyinstaller $pyInstInstArgs
if ($LASTEXITCODE -ne 0) { Write-Error "PyInstaller failed for installer GUI"; exit 1 }

# Collect artifacts
$buildOut = Join-Path $RepoRoot "dist"
$svcExe = Join-Path $buildOut ("$svcName.exe")
$instExe = Join-Path $buildOut ("$instName.exe")

if (-not (Test-Path $svcExe)) { Write-Error "Service EXE not found: $svcExe"; exit 1 }
if (-not (Test-Path $instExe)) { Write-Error "Installer EXE not found: $instExe"; exit 1 }

Copy-Item $svcExe -Destination $distDir -Force
Copy-Item $instExe -Destination $distDir -Force

# Copy config template and NSIS script
Copy-Item "$RepoRoot\packaging\install.nsi" -Destination $distDir -Force
Copy-Item "$RepoRoot\packaging\resources\config.json.template" -Destination $distDir -Force

Push-Location $distDir
try {
    Write-Host "Running makensis to build installer using: $MakensisExe"
    & $MakensisExe -V2 "install.nsi"
    if ($LASTEXITCODE -ne 0) { Write-Error "makensis failed"; exit 1 }
    Write-Host "Installer built: $(Get-ChildItem -Filter *.exe | Select-Object -First 1).FullName"
} finally {
    Pop-Location
}

Write-Host "Build complete. Artifacts are in: $distDir"
