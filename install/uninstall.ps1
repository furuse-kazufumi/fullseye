<#
.SYNOPSIS
    Uninstaller for Fullseye + Fullseye Studio (Windows).

.DESCRIPTION
    Removes the "Fullseye Studio" shortcuts from the Desktop and Start Menu and
    uninstalls the `fullseye` package. If a project venv (<repo>\.venv) exists,
    the package is removed from that venv; otherwise it is removed from the user
    site-packages. The venv directory itself is kept unless -RemoveVenv is given.
    The script is idempotent - missing shortcuts / package are silently skipped.

.PARAMETER RepoRoot
    Path to the Fullseye repository root. Defaults to the parent of this script's
    folder (this script lives in <repo>\install).

.PARAMETER RemoveVenv
    Also delete the <repo>\.venv directory.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File install\uninstall.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File install\uninstall.ps1 -RemoveVenv
#>
[CmdletBinding()]
param(
    [string]$RepoRoot,
    [switch]$RemoveVenv
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}
$RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path

Write-Host "Fullseye uninstaller" -ForegroundColor Green
Write-Host "Repository: $RepoRoot"

# --------------------------------------------------------------------------- #
# 1. Remove shortcuts from Desktop and Start Menu.
# --------------------------------------------------------------------------- #
$shortcutName = "Fullseye Studio.lnk"
$desktop  = [Environment]::GetFolderPath('Desktop')
$programs = [Environment]::GetFolderPath('Programs')
foreach ($dir in @($desktop, $programs)) {
    if ([string]::IsNullOrWhiteSpace($dir)) { continue }
    $lnkPath = Join-Path $dir $shortcutName
    if (Test-Path -LiteralPath $lnkPath) {
        Remove-Item -LiteralPath $lnkPath -Force
        Write-Host "Removed shortcut: $lnkPath"
    }
}

# --------------------------------------------------------------------------- #
# 2. Uninstall the fullseye package (from venv if present, else user-site).
# --------------------------------------------------------------------------- #
$venvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $venvPython) {
    Write-Host "Uninstalling 'fullseye' from venv..."
    & $venvPython -m pip uninstall fullseye -y
} else {
    Write-Host "Uninstalling 'fullseye' from user site-packages..."
    & py -3.11 -m pip uninstall fullseye -y
}

# --------------------------------------------------------------------------- #
# 3. Optionally remove the venv directory.
# --------------------------------------------------------------------------- #
if ($RemoveVenv) {
    $venvDir = Join-Path $RepoRoot ".venv"
    if (Test-Path -LiteralPath $venvDir) {
        Write-Host "Removing venv: $venvDir"
        Remove-Item -LiteralPath $venvDir -Recurse -Force
    }
}

Write-Host ""
Write-Host "Uninstall complete." -ForegroundColor Green
exit 0
