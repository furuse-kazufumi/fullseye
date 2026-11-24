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

function Stop-Uninstaller([string]$what, [string]$why, [string]$fix) {
    # Explain failure and a pasteable repair in both languages / 英日ともに原因と貼り付け可能な対処を示す。
    Write-Host "Uninstall stopped: $what" -ForegroundColor Red
    Write-Host "Why: $why"
    Write-Host "Fix: $fix"
    Write-Host "アンインストールを停止しました: $what" -ForegroundColor Red
    Write-Host "理由: $why"
    Write-Host "対処（そのまま貼り付け可能）: $fix"
    exit 1
}

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
# Current installs use Programs\Fullseye; the two flat locations are legacy.
# 現行の Programs\Fullseye と、旧版の平坦な二つの場所を対象にする。
$shortcutDirs = @($desktop, $programs)
if (-not [string]::IsNullOrWhiteSpace($programs)) {
    $shortcutDirs += (Join-Path $programs "Fullseye")
}
foreach ($dir in $shortcutDirs) {
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
try {
    if (Test-Path -LiteralPath $venvPython) {
        Write-Host "Uninstalling 'fullseye' from venv..."
        & $venvPython -m pip uninstall fullseye -y
        $uninstallFix = "`"${venvPython}`" -m pip uninstall fullseye -y"
    } else {
        Write-Host "Uninstalling 'fullseye' from user site-packages..."
        & py -3.11 -m pip uninstall fullseye -y
        $uninstallFix = "py -3.11 -m pip uninstall fullseye -y"
    }
} catch {
    Stop-Uninstaller "pip could not be started: $($_.Exception.Message)" "Python could not launch pip, so package removal was not attempted." "Run: fullseye doctor; then retry: py -3.11 -m pip uninstall fullseye -y"
}
if ($LASTEXITCODE -ne 0) {
    Stop-Uninstaller "pip uninstall fullseye failed (exit code $LASTEXITCODE)." "pip reported that the package could not be removed, so the uninstaller will not report success or remove the venv." "Run: $uninstallFix; then run: fullseye doctor"
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
