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
    Comma-separated pip "extras" to install. Default "all,gui" installs every
    optional backend (opencv / scikit-image / Pillow / PyWavelets / torch /
    kornia / mahotas / SimpleITK) PLUS the PySide6 GUI that Fullseye Studio
    needs. NOTE: the pyproject "all" extra does NOT include the GUI, so "gui"
    is added explicitly here.

.PARAMETER Minimal
    Install only the "gui" extra (core numpy/scipy + PySide6). This is a small,
    fast install that runs Fullseye Studio and the ~75 core operators, but skips
    the heavy optional backends (torch, opencv, ...). Overrides -Extras.

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
    [string]$Extras = "all,gui",
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
    Write-Error "pyproject.toml not found under '$RepoRoot'. Pass the repo root with -RepoRoot <path>."
    exit 1
}
$studioPy = Join-Path $RepoRoot "studio.py"
if (-not (Test-Path -LiteralPath $studioPy)) {
    Write-Error "studio.py not found under '$RepoRoot'. Is this the Fullseye repository?"
    exit 1
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
    Write-Host ""
    Write-Host "Python 3.11 was not found (the 'py -3.11' launcher failed)." -ForegroundColor Red
    Write-Host "Please install Python 3.11 (64-bit) from:"
    Write-Host "    https://www.python.org/downloads/release/python-3119/"
    Write-Host "During setup, tick 'Add python.exe to PATH' and 'py launcher'."
    Write-Host "Then re-run this installer."
    exit 1
}

# --------------------------------------------------------------------------- #
# 3. Decide the extras string.
# --------------------------------------------------------------------------- #
if ($Minimal) {
    $Extras = "gui"
}
Write-Host "Extras: [$Extras]"

# The editable-install target. Brackets select the extras; this must stay a
# single argument, so we build it as one quoted string.
$pipTarget = "$RepoRoot[$Extras]"

# --------------------------------------------------------------------------- #
# 4. Install (venv by default, or --user site with -UserSite).
# --------------------------------------------------------------------------- #
$venvDir    = Join-Path $RepoRoot ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$venvPythonw = Join-Path $venvDir "Scripts\pythonw.exe"

if ($UserSite) {
    Write-Section "Installing into user site-packages"
    & py -3.11 -m pip install -U pip
    if ($LASTEXITCODE -ne 0) { Write-Error "pip upgrade failed."; exit 1 }
    & py -3.11 -m pip install --user -e $pipTarget
    if ($LASTEXITCODE -ne 0) { Write-Error "pip install failed."; exit 1 }
    $installPython = "py -3.11"
}
else {
    Write-Section "Preparing virtual environment"
    if (Test-Path -LiteralPath $venvPython) {
        Write-Host "Reusing existing venv: $venvDir"
    } else {
        Write-Host "Creating venv: $venvDir"
        & py -3.11 -m venv $venvDir
        if ($LASTEXITCODE -ne 0) { Write-Error "venv creation failed."; exit 1 }
    }

    Write-Section "Installing Fullseye (editable)"
    & $venvPython -m pip install -U pip
    if ($LASTEXITCODE -ne 0) { Write-Error "pip upgrade failed."; exit 1 }
    & $venvPython -m pip install -e $pipTarget
    if ($LASTEXITCODE -ne 0) { Write-Error "pip install failed."; exit 1 }
    $installPython = $venvPython
}

# --------------------------------------------------------------------------- #
# 5. Resolve the pythonw.exe used to launch the GUI without a console window.
# --------------------------------------------------------------------------- #
function Resolve-Pythonw {
    param([string]$VenvPythonw)
    # Prefer the venv's windowed interpreter.
    if (Test-Path -LiteralPath $VenvPythonw) { return $VenvPythonw }
    # Otherwise derive pythonw.exe next to the interpreter the py launcher uses.
    try {
        $exe = & py -3.11 -c "import sys, os; print(os.path.join(os.path.dirname(sys.executable), 'pythonw.exe'))" 2>$null
        if ($LASTEXITCODE -eq 0 -and $exe -and (Test-Path -LiteralPath $exe.Trim())) {
            return $exe.Trim()
        }
    } catch { }
    # Last resort: the Windows windowed launcher on PATH.
    $pyw = Get-Command pyw.exe -ErrorAction SilentlyContinue
    if ($pyw) { return $pyw.Source }
    return $null
}

# --------------------------------------------------------------------------- #
# 6. Create the shortcuts.
# --------------------------------------------------------------------------- #
if (-not $NoShortcut) {
    Write-Section "Creating shortcuts"
    $launcher = Resolve-Pythonw -VenvPythonw $venvPythonw
    if ($null -eq $launcher) {
        Write-Host "Could not locate pythonw.exe; skipping shortcut creation." -ForegroundColor Yellow
        Write-Host "You can still launch with:  fullseye-studio   or   py -3.11 studio.py"
    } else {
        $iconPath = Join-Path $RepoRoot "assets\fullseye.ico"
        $shortcutName = "Fullseye Studio.lnk"
        $desktop  = [Environment]::GetFolderPath('Desktop')
        $programs = [Environment]::GetFolderPath('Programs')

        $shell = New-Object -ComObject WScript.Shell
        foreach ($dir in @($desktop, $programs)) {
            if ([string]::IsNullOrWhiteSpace($dir)) { continue }
            if (-not (Test-Path -LiteralPath $dir)) {
                New-Item -ItemType Directory -Path $dir -Force | Out-Null
            }
            $lnkPath = Join-Path $dir $shortcutName
            $sc = $shell.CreateShortcut($lnkPath)
            $sc.TargetPath       = $launcher
            # Quote the script path so a repo path with spaces still works.
            $sc.Arguments        = '"' + $studioPy + '"'
            $sc.WorkingDirectory = $RepoRoot
            if (Test-Path -LiteralPath $iconPath) {
                $sc.IconLocation = "$iconPath,0"
            }
            $sc.Description = "Fullseye Studio - visual image-processing pipeline workbench"
            $sc.Save()
            Write-Host "Created: $lnkPath"
        }
        Write-Host "Shortcut target : $launcher"
        Write-Host "Shortcut args   : `"$studioPy`""
    }
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
