<#
.SYNOPSIS
    Uninstaller for Fullseye + Fullseye Studio (Windows).

.DESCRIPTION
    First removes only the files and registry entry recorded by Fullseye's install
    ledger, then uninstalls the `fullseye` package. If a project venv
    (<repo>\.venv) exists, the package is removed from that venv; otherwise it is
    removed from the user site-packages. The venv directory itself is kept unless
    -RemoveVenv is given. A broken or absent package uses a guarded legacy fallback:
    it lists every candidate first and never removes a file absent from the ledger.
    まず Fullseye の台帳に記録したファイルとレジストリ項目だけを消してから、
    `fullseye` パッケージを削除します。パッケージが壊れているか無い場合だけ、
    全候補を先に表示し、台帳に無いファイルを決して消さない旧経路に切り替えます。

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
# 1. Prefer Fullseye's ledger-aware uninstaller. It verifies the ledger and file
#    contents before removing a shortcut, icon, .cmd, or Apps & features entry.
#    Fullseye の台帳対応アンインストーラを優先し、削除前に台帳と内容を検証する。
#    pip is deliberately left to this wrapper so -RemoveVenv remains synchronous
#    and fail-closed. / pip はこのラッパーで同期実行し、-RemoveVenv も失敗時に停止する。
# --------------------------------------------------------------------------- #
function Test-LedgerEntry([object[]]$Entries, [string]$Kind, [string]$Path) {
    foreach ($entry in $Entries) {
        if ($null -eq $entry) { continue }
        if ([string]$entry.kind -eq $Kind -and
            [string]::Equals([string]$entry.path, $Path, [StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }
    return $false
}

function Get-FullseyeKnownFolder([string]$Name) {
    # pytest は Windows shell folder API の返す利用者の場所ではなく、一時フォルダを
    # 渡す。通常のアンインストールでこの環境変数は無いので、実際の既知フォルダを使う。
    # pytest redirects known folders to a temporary root.  Ordinary uninstall
    # runs have no test override and keep the Windows-known-folder behaviour.
    if ($env:FULLSEYE_TEST_ISOLATION -eq "1") {
        $override = switch ($Name) {
            "Desktop" { $env:FULLSEYE_TEST_DESKTOP; break }
            "Programs" { $env:FULLSEYE_TEST_PROGRAMS; break }
            "LocalApplicationData" { $env:FULLSEYE_TEST_LOCALAPPDATA; break }
            default { $null }
        }
        if (-not [string]::IsNullOrWhiteSpace($override)) {
            return $override
        }
    }
    return [Environment]::GetFolderPath($Name)
}

function Invoke-LegacyLedgerFallback {
    # Python/fullseye が壊れたときだけの旧経路。名前だけでは消さず、台帳に記録された固定候補だけに限定する。
    # Legacy fallback for a broken package: names are never enough; only recorded fixed candidates are removable.
    $desktop = Get-FullseyeKnownFolder 'Desktop'
    $programs = Get-FullseyeKnownFolder 'Programs'
    $localAppData = Get-FullseyeKnownFolder 'LocalApplicationData'
    $setupDir = Join-Path $localAppData "Fullseye\setup"
    $ledgerPath = if ([string]::IsNullOrWhiteSpace($env:FULLSEYE_LEDGER)) {
        Join-Path $setupDir "install_ledger.json"
    } else {
        $env:FULLSEYE_LEDGER
    }
    $candidates = @(
        (Join-Path $setupDir "fullseye.ico"),
        (Join-Path $setupDir "fullseye-uninstall.cmd"),
        (Join-Path $setupDir "fullseye-auto-shortcuts.json")
    )
    foreach ($dir in @($desktop, $programs)) {
        if (-not [string]::IsNullOrWhiteSpace($dir)) {
            $candidates += (Join-Path $dir "Fullseye Studio.lnk")
        }
    }
    if (-not [string]::IsNullOrWhiteSpace($programs)) {
        $candidates += (Join-Path $programs "Fullseye\Fullseye Studio.lnk")
    }
    $registryPath = if ($env:FULLSEYE_TEST_ISOLATION -eq "1" -and
                         -not [string]::IsNullOrWhiteSpace($env:FULLSEYE_ISOLATED_UNINSTALL_KEY)) {
        $env:FULLSEYE_ISOLATED_UNINSTALL_KEY
    } else {
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\Fullseye"
    }
    $registryDrivePath = "HKCU:\$registryPath"
    $entries = @()
    try {
        if (-not (Test-Path -LiteralPath $ledgerPath)) { throw "the install ledger does not exist" }
        $ledger = Get-Content -LiteralPath $ledgerPath -Raw -Encoding utf8 | ConvertFrom-Json
        if ($null -eq $ledger.entries) { throw "the install ledger has no entries array" }
        $entries = @($ledger.entries)
    } catch {
        Write-Host "Package cleanup is unavailable and the legacy ledger cannot be read: $($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host "Why: deleting by name could remove a file created by you with the same name."
        Write-Host "Fix: run fullseye doctor, repair or reinstall Fullseye, then run this uninstaller again."
        Write-Host "パッケージ後始末を使えず、旧台帳も読めません: $($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host "理由: 名前だけで消すと、同名で利用者が作成したファイルを消すおそれがあります。"
        Write-Host "対処: fullseye doctor を実行し、Fullseye を修復または再導入してからこのアンインストーラを再実行してください。"
        foreach ($path in $candidates) {
            if (Test-Path -LiteralPath $path) { Write-Host "Kept (not in a readable ledger): $path" }
        }
        if (Test-Path -LiteralPath $registryDrivePath) { Write-Host "Kept (not in a readable ledger): $registryDrivePath" }
        return
    }

    Write-Host "Legacy fallback plan (only paths recorded in the ledger will be removed):"
    $remove = @()
    foreach ($path in $candidates) {
        if (-not (Test-Path -LiteralPath $path)) { continue }
        if (Test-LedgerEntry $entries "file" $path) {
            Write-Host "  Remove: $path"
            $remove += $path
        } else {
            Write-Host "  Keep (not in ledger): $path"
        }
    }
    $removeRegistry = $false
    if (Test-Path -LiteralPath $registryDrivePath) {
        if (Test-LedgerEntry $entries "regkey" $registryPath) {
            Write-Host "  Remove: $registryDrivePath"
            $removeRegistry = $true
        } else {
            Write-Host "  Keep (not in ledger): $registryDrivePath"
        }
    }
    foreach ($path in $remove) {
        Remove-Item -LiteralPath $path -Force
        Write-Host "Removed recorded item: $path"
    }
    if ($removeRegistry) {
        Remove-Item -LiteralPath $registryDrivePath -Force
        Write-Host "Removed recorded Apps & features entry: $registryDrivePath"
    }
}

$venvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$ledgerProbe = "import fullseye, fullseye.uninstall"
$ledgerCleanup = 'from fullseye import uninstall; raise SystemExit(uninstall.main(["--uninstall", "--yes"], pip_externally_managed=True))'
$ledgerReady = $false
try {
    if (Test-Path -LiteralPath $venvPython) {
        & $venvPython -I -c $ledgerProbe
    } else {
        & py -3.11 -I -c $ledgerProbe
    }
    $ledgerReady = ($LASTEXITCODE -eq 0)
} catch {
    $ledgerReady = $false
}
if ($ledgerReady) {
    Write-Host "Removing Fullseye setup artifacts recorded in the install ledger..."
    try {
        if (Test-Path -LiteralPath $venvPython) {
            & $venvPython -I -c $ledgerCleanup
        } else {
            & py -3.11 -I -c $ledgerCleanup
        }
    } catch {
        Stop-Uninstaller "the ledger-based Fullseye cleanup could not be started: $($_.Exception.Message)" "The package was available, so falling back to names could delete a user-created file." "Run: fullseye doctor; then retry this uninstaller."
    }
    if ($LASTEXITCODE -ne 0) {
        Stop-Uninstaller "the ledger-based Fullseye cleanup failed (exit code $LASTEXITCODE)." "The install ledger reported an item that could not be safely removed, so the name-based fallback was not used." "Run: fullseye doctor; inspect the listed paths; then retry this uninstaller."
    }
} else {
    Invoke-LegacyLedgerFallback
}

# --------------------------------------------------------------------------- #
# 2. Uninstall the fullseye package (from venv if present, else user-site).
# --------------------------------------------------------------------------- #
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
