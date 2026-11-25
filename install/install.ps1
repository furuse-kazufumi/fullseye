<#
.SYNOPSIS
    Fullseye + Fullseye Studio installer for Windows.

.DESCRIPTION
    Sets up everything needed to run Fullseye (the image-processing operator
    library / pipeline designer) and Fullseye Studio (the PySide6 GUI) with a
    single command. By default it:

        1. Verifies Python 3.11 is available (via the `py -3.11` launcher).
        2. Creates a virtual environment at <repo>\.venv (skipped if it exists).
        3. Installs Fullseye in editable mode with the requested extras.
        4. Creates "Fullseye Studio" shortcuts on the Desktop and Start Menu.

    The script is idempotent: re-running it reuses the existing venv, upgrades
    the install, and overwrites the shortcuts. It never asks interactive
    questions, so it is safe to run unattended.

.PARAMETER RepoRoot
    Path to the Fullseye repository root. Defaults to the parent of the folder
    containing this script (i.e. the repo, since this script lives in
    <repo>\install).

.PARAMETER Extras
    Comma-separated pip "extras" to install. Default "all" installs every
    compatible backend. The installer adds GPU dependencies only when
    Fullseye's CUDA probe confirms an NVIDIA/CUDA environment. Fullseye Studio
    and Pillow are standard dependencies, so they are installed even without an extra.

.PARAMETER Minimal
    Install only the standard dependencies (core numpy/scipy + Studio + Pillow).
    This is a small, fast install that skips the heavy optional backends
    (torch, opencv, ...). Overrides -Extras.

.PARAMETER UserSite
    Install into the user site-packages (py -3.11 -m pip install --user) instead
    of creating a venv. The shortcut then targets the system pythonw.exe.

.PARAMETER NoShortcut
    Skip creation of the Desktop / Start Menu shortcuts.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File install\install.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File install\install.ps1 -Minimal

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File install\install.ps1 -UserSite -Extras "gui,opencv"
#>
[CmdletBinding()]
param(
    [string]$RepoRoot,
    [string]$Extras = "all",
    [switch]$Minimal,
    [switch]$UserSite,
    [switch]$NoShortcut
)

# Fail fast on any error so a half-broken install is never reported as success.
$ErrorActionPreference = "Stop"

function Write-Section([string]$msg) {
    Write-Host ""
    Write-Host "== $msg ==" -ForegroundColor Cyan
}

function Stop-Installer([string]$what, [string]$why, [string]$fix) {
    # Windows users need the event, its reason, and a pasteable recovery command.
    Write-Host "Installation stopped: $what" -ForegroundColor Red
    Write-Host "Why: $why"
    Write-Host "Fix: $fix"
    Write-Host "発生したこと: $what" -ForegroundColor Red
    Write-Host "理由: $why"
    Write-Host "対処（そのまま貼り付け可能）: $fix"
    exit 1
}

# --------------------------------------------------------------------------- #
# 1. Resolve the repository root and sanity-check it.
# --------------------------------------------------------------------------- #
if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    # This script lives in <repo>\install, so the repo root is its parent.
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}
$RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path

$pyproject = Join-Path $RepoRoot "pyproject.toml"
if (-not (Test-Path -LiteralPath $pyproject)) {
    Stop-Installer "pyproject.toml was not found under ${RepoRoot}." "The selected folder is not a Fullseye checkout." "Pass its root: powershell -ExecutionPolicy Bypass -File install\install.ps1 -RepoRoot [path-to-fullseye]"
}
$studioPy = Join-Path $RepoRoot "studio.py"
if (-not (Test-Path -LiteralPath $studioPy)) {
    Stop-Installer "studio.py was not found under ${RepoRoot}." "The selected folder does not contain the Studio launcher." "Pass its root: powershell -ExecutionPolicy Bypass -File install\install.ps1 -RepoRoot [path-to-fullseye]"
}

Write-Host "Fullseye installer" -ForegroundColor Green
Write-Host "Repository: $RepoRoot"

# --------------------------------------------------------------------------- #
# 2. Verify Python 3.11 is available.
# --------------------------------------------------------------------------- #
Write-Section "Checking Python 3.11"
$pyOk = $false
try {
    $ver = & py -3.11 --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        $pyOk = $true
        Write-Host "Found: $ver"
    }
} catch {
    $pyOk = $false
}
if (-not $pyOk) {
    Stop-Installer "Python 3.11 was not found (the 'py -3.11' launcher failed)." "The installer needs that interpreter to create its isolated environment." "Install Python 3.11 (64-bit) from https://www.python.org/downloads/release/python-3119/ with 'py launcher', then run this command again."
}

# --------------------------------------------------------------------------- #
# 3. Decide the extras string.
# --------------------------------------------------------------------------- #
$installAll = (-not $Minimal) -and ($Extras.Trim().ToLowerInvariant() -eq "all")
if ($Minimal) {
    $Extras = ""
}
elseif ($installAll) {
    # ``all`` cannot subtract an extra. Start with this explicit CPU subset,
    # then use setup_cmd.cuda_available() after the base install to add [gpu].
    $Extras = "all-cpu"
}
Write-Host "Optional extras: [$Extras]"

# The editable-install target. Brackets select the extras; this must stay a
# single argument, so we build it as one quoted string.
$pipTarget = if ([string]::IsNullOrWhiteSpace($Extras)) { $RepoRoot } else { "${RepoRoot}[$Extras]" }

# --------------------------------------------------------------------------- #
# 4. Install (venv by default, or --user site with -UserSite).
# --------------------------------------------------------------------------- #
$venvDir    = Join-Path $RepoRoot ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

if ($UserSite) {
    Write-Section "Installing into user site-packages"
    & py -3.11 -m pip install -U pip
    if ($LASTEXITCODE -ne 0) { Stop-Installer "pip could not be upgraded (exit code $LASTEXITCODE)." "The Python package installer returned an error before Fullseye was installed." "Run: py -3.11 -m pip install -U pip; then rerun this installer. If it still fails, run: fullseye doctor" }
    & py -3.11 -m pip install --user -e $pipTarget
    if ($LASTEXITCODE -ne 0) { Stop-Installer "Fullseye could not be installed (exit code $LASTEXITCODE)." "pip rejected the requested dependencies or could not reach a package source." "Run: py -3.11 -m pip install --user -e `"${RepoRoot}`"; then rerun this installer. If it still fails, run: fullseye doctor" }
    $installPython = "py -3.11"
}
else {
    Write-Section "Preparing virtual environment"
    if (Test-Path -LiteralPath $venvPython) {
        Write-Host "Reusing existing venv: $venvDir"
    } else {
        Write-Host "Creating venv: $venvDir"
        & py -3.11 -m venv $venvDir
        if ($LASTEXITCODE -ne 0) { Stop-Installer "The virtual environment ${venvDir} could not be created (exit code $LASTEXITCODE)." "Python could not create the isolated install location." "Run: py -3.11 -m venv `"${venvDir}`"; then rerun this installer. If it still fails, run: fullseye doctor" }
    }

    Write-Section "Installing Fullseye (editable)"
    & $venvPython -m pip install -U pip
    if ($LASTEXITCODE -ne 0) { Stop-Installer "pip in ${venvDir} could not be upgraded (exit code $LASTEXITCODE)." "The virtual environment package installer returned an error before Fullseye was installed." "Run: `"${venvPython}`" -m pip install -U pip; then rerun this installer. If it still fails, run: fullseye doctor" }
    & $venvPython -m pip install -e $pipTarget
    if ($LASTEXITCODE -ne 0) { Stop-Installer "Fullseye could not be installed into ${venvDir} (exit code $LASTEXITCODE)." "pip rejected the requested dependencies or could not reach a package source." "Run: `"${venvPython}`" -m pip install -e `"${RepoRoot}`"; then rerun this installer. If it still fails, run: fullseye doctor" }
    $installPython = $venvPython
}

# --------------------------------------------------------------------------- #
# 5. ``all`` の GPU 群は、Fullseye setup と同じ CUDA 判定でだけ追加する。
# --------------------------------------------------------------------------- #
if ($installAll) {
    if ($UserSite) {
        & py -3.11 -P -c "from fullseye.setup_cmd import cuda_available; raise SystemExit(0 if cuda_available() else 1)"
    } else {
        & $venvPython -P -c "from fullseye.setup_cmd import cuda_available; raise SystemExit(0 if cuda_available() else 1)"
    }
    if ($LASTEXITCODE -eq 0) {
        Write-Section "Installing GPU extras (CUDA detected)"
        if ($UserSite) {
            & py -3.11 -m pip install --user -e "${RepoRoot}[gpu]"
        } else {
            & $venvPython -m pip install -e "${RepoRoot}[gpu]"
        }
        $gpuRepair = if ($UserSite) { "py -3.11 -m pip install --user -e `"${RepoRoot}[gpu]`"; fullseye doctor" } else { "`"${venvPython}`" -m pip install -e `"${RepoRoot}[gpu]`"; fullseye doctor" }
        if ($LASTEXITCODE -ne 0) { Stop-Installer "The CUDA GPU extras could not be installed (exit code $LASTEXITCODE)." "Fullseye detected CUDA, but pip could not install torch, kornia, or CuPy for this Python." "Run: $gpuRepair" }
    } else {
        Write-Host "CUDA was not detected; installed [all-cpu] and skipped the GPU group (torch, kornia, CuPy)." -ForegroundColor Yellow
        Write-Host "Why: Fullseye's shared CUDA probe requires a working nvidia-smi, so this installer does not download GPU packages on a CPU-only PC."
        Write-Host "Fix: install an NVIDIA driver/CUDA, confirm with nvidia-smi, then rerun: powershell -ExecutionPolicy Bypass -File install\install.ps1 -Extras all; diagnose with: fullseye doctor"
        Write-Host "CUDA を検出できなかったため、[all-cpu] を入れ、GPU 群(torch / kornia / CuPy)は入れませんでした。" -ForegroundColor Yellow
        Write-Host "理由: Fullseye 共通の CUDA 判定は nvidia-smi の成功を必要とするため、CPU 専用 PC に GPU パッケージをダウンロードしません。"
        Write-Host "対処: NVIDIA driver/CUDA を入れ nvidia-smi で確認してから、powershell -ExecutionPolicy Bypass -File install\install.ps1 -Extras all を再実行してください。診断: fullseye doctor"
    }
}

# --------------------------------------------------------------------------- #
# 6. Create Unicode-safe shortcuts through the package implementation.
# --------------------------------------------------------------------------- #
if (-not $NoShortcut) {
    Write-Section "Creating shortcuts"
    $shortcutCode = "from fullseye import shortcuts; [print('Created: ' + str(p)) for p in shortcuts.install(desktop=True)]"
    if ($UserSite) {
        & py -3.11 -P -c $shortcutCode
    } else {
        & $venvPython -P -c $shortcutCode
    }
    $shortcutRepair = if ($UserSite) { "py -3.11 -P -m studio --install-shortcuts" } else { "`"${venvPython}`" -P -m studio --install-shortcuts" }
    if ($LASTEXITCODE -ne 0) { Stop-Installer "The Fullseye Studio shortcut could not be created (exit code $LASTEXITCODE)." "The Unicode-safe Fullseye shortcut helper could not write the Start Menu or Desktop entry." "Run: fullseye doctor; then retry: $shortcutRepair" }
}

# --------------------------------------------------------------------------- #
# 7. Done - how to launch.
# --------------------------------------------------------------------------- #
Write-Section "Installation complete"
Write-Host "Launch Fullseye Studio any of these ways:"
Write-Host "  - Desktop / Start Menu shortcut:  'Fullseye Studio'"
if ($UserSite) {
    Write-Host "  - Console script:                 fullseye-studio"
    Write-Host "  - Direct:                         py -3.11 `"$studioPy`""
} else {
    Write-Host "  - Console script (from venv):     $venvDir\Scripts\fullseye-studio.exe"
    Write-Host "  - Direct:                         $venvPython `"$studioPy`""
}
Write-Host ""
Write-Host "CLI (Fullseye):"
if ($UserSite) {
    Write-Host "  - fullseye --help"
} else {
    Write-Host "  - $venvDir\Scripts\fullseye.exe --help"
}
Write-Host ""
exit 0
