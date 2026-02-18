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

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
# Repo root should be one level up from the packaging directory (the repository root)
$RepoRootObj = Resolve-Path (Join-Path $ScriptDir '..') -ErrorAction SilentlyContinue
if (-not $RepoRootObj) { $RepoRootObj = Get-Location }
# Normalize to a single string path (Resolve-Path may return PathInfo objects)
$RepoRootPath = $RepoRootObj | Select-Object -First 1 | ForEach-Object { if ($_.PSObject.Properties.Match('Path')) { $_.Path } else { $_.ToString() } }
if (-not $RepoRootPath) { $RepoRootPath = (Get-Location).Path }

# Ensure output directory exists inside the repository
$resolvedOut = Join-Path $RepoRootPath $OutputDir
if (-not (Test-Path $resolvedOut)) { New-Item -ItemType Directory -Path $resolvedOut -Force | Out-Null }
$distDir = Resolve-Path $resolvedOut | Select-Object -ExpandProperty Path

Write-Host "Building service EXE (service_wrapper)..."
$svcSpec = "agent/service_wrapper.py"
$svcName = "TallyBackupAgent"
$svcArgs = @("--noconsole","--clean")

$pyInstSvcArgs = @("--onefile","--name",$svcName,$svcSpec) + $svcArgs
if ($IconPath) { $pyInstSvcArgs += @("--icon",$IconPath) }

Write-Host "PyInstaller args for service: $($pyInstSvcArgs -join ' ')"
& pyinstaller @pyInstSvcArgs
if ($LASTEXITCODE -ne 0) { Write-Error "PyInstaller failed for service"; exit 1 }

Write-Host "Building installer GUI EXE (installer_gui)..."
$instSpec = "tools/installer_gui.py"
$instName = "TallyBackupInstaller"
$instArgs = @("--noconsole")

$pyInstInstArgs = @("--onefile","--name",$instName,$instSpec) + $instArgs
if ($IconPath) { $pyInstInstArgs += @("--icon",$IconPath) }

Write-Host "PyInstaller args for installer GUI: $($pyInstInstArgs -join ' ')"
& pyinstaller @pyInstInstArgs
if ($LASTEXITCODE -ne 0) { Write-Error "PyInstaller failed for installer GUI"; exit 1 }

# Collect artifacts: locate generated EXEs even if checkout path is nested
$svcExe = $null
$instExe = $null

# First, check obvious dist folder under repo root
$candidates = @(
    Join-Path $RepoRootPath "dist\$svcName.exe",
    Join-Path $RepoRootPath "dist\$instName.exe",
    Join-Path $RepoRootPath "..\dist\$svcName.exe",
    Join-Path $RepoRootPath "..\dist\$instName.exe"
)

foreach ($cand in $candidates) {
    if ((Test-Path $cand) -and ($svcExe -eq $null) -and ($cand -like "*$svcName.exe")) { $svcExe = (Resolve-Path $cand).Path }
    if ((Test-Path $cand) -and ($instExe -eq $null) -and ($cand -like "*$instName.exe")) { $instExe = (Resolve-Path $cand).Path }
}

# If not found, search recursively for the expected EXE names (handles nested checkout dirs)
if (-not $svcExe) {
    $found = Get-ChildItem -Path $RepoRootPath -Filter "$svcName.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) { $svcExe = $found.FullName }
}
if (-not $instExe) {
    $found = Get-ChildItem -Path $RepoRootPath -Filter "$instName.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) { $instExe = $found.FullName }
}

if (-not $svcExe) { Write-Error "Service EXE not found under repo: $svcName.exe"; exit 1 }
if (-not $instExe) { Write-Error "Installer EXE not found under repo: $instName.exe"; exit 1 }

Write-Host "Found service EXE: $svcExe"
Write-Host "Found installer EXE: $instExe"

Copy-Item $svcExe -Destination $distDir -Force
Copy-Item $instExe -Destination $distDir -Force

# Copy config template and NSIS script
Copy-Item (Join-Path $RepoRootPath 'packaging\install.nsi') -Destination $distDir -Force
Copy-Item (Join-Path $RepoRootPath 'packaging\resources\config.json.template') -Destination $distDir -Force

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
