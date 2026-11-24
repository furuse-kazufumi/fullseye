# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""``fullseye doctor`` — 起動を妨げる環境を、直せる手順つきで診断する。 / Diagnose startup environments with copyable repairs.

This module deliberately does not install packages, edit the registry, or contact a
network service while collecting facts.  ``--fix`` is limited to a reversible stale
per-user Qt setting, shows its plan first, and requires an interactive confirmation.
A terminal without a console and CI are therefore inspection-only by design.
"""
from __future__ import annotations

import argparse
import codecs
import importlib.metadata
import importlib.util
import json
import os
import ssl
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Sequence


# 日英のトラブルシューティング表と同じ順に保つ。 / Keep the order of both troubleshooting tables.
# drift 試験は重複したリストを信じず、両文書の ``<!-- doctor: ID -->`` を読む。 / The drift test reads both docs.
TROUBLESHOOTING_IDS = (
    "console_encoding", "long_path", "unicode_space_path", "onedrive_known_folders",
    "store_python", "conda_pythonw", "python_path", "multiple_python", "pip_target",
    "native_dll", "antivirus_lock", "powershell_policy", "proxy_certificate",
    "write_permission", "high_dpi", "cuda_driver", "smartscreen",
)


def _command(*parts: str) -> str:
    """PowerShell のコピーペースト用に現在の Python を引用する。 / Quote the current Python for PowerShell."""
    return " ".join('"%s"' % p.replace('"', '`"') if any(c in p for c in " \t") else p for p in parts)


def _item(
    ident: str, status: str, what: str, checked: str, fix: str,
    commands: Sequence[str] = (), *, detail: str = "", fixable: bool = False,
) -> dict[str, Any]:
    """診断 1 件を JSON と人間向け表示で共有する形にする。 / Make one shared text/JSON finding."""
    return {"id": ident, "status": status, "what": what, "checked": checked,
            "detail": detail, "fix": fix, "commands": list(commands), "fixable": fixable}


def _is_windows(context: dict[str, Any]) -> bool:
    return bool(context.get("platform", sys.platform).startswith("win"))


def _is_ascii_path(path: str) -> bool:
    try:
        path.encode("ascii")
    except UnicodeEncodeError:
        return False
    return True


def _read_long_paths() -> Optional[bool]:
    """LongPathsEnabled を読むだけで調べる。 / Read, never alter, the Windows long-path setting."""
    if sys.platform != "win32":
        return None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SYSTEM\CurrentControlSet\Control\FileSystem") as key:
            return bool(winreg.QueryValueEx(key, "LongPathsEnabled")[0])
    except OSError:
        return None


def _windows_known_folder_env(env: dict[str, str]) -> tuple[bool, str]:
    """OneDrive へ既知フォルダーが移った可能性を環境変数から示す。 / Find known OneDrive redirection clues."""
    candidates = [env.get("OneDrive", ""), env.get("OneDriveConsumer", ""),
                  env.get("OneDriveCommercial", ""), env.get("USERPROFILE", "")]
    moved = [p for p in candidates if p and "onedrive" in p.lower()]
    return bool(moved), "; ".join(moved)


def _distribution_root() -> Optional[Path]:
    try:
        return Path(importlib.metadata.distribution("fullseye").locate_file(""))
    except importlib.metadata.PackageNotFoundError:
        return None


def _sdk_doctor() -> Optional[dict[str, Any]]:
    """SDK 便の診断が入っていれば呼ぶだけで、結果を包む。 / Delegate to the SDK doctor when present."""
    try:
        if importlib.util.find_spec("fullseye.sdk") is None:
            return None
    except (ImportError, ValueError):
        return None
    try:
        run = subprocess.run([sys.executable, "-m", "fullseye.sdk", "--doctor", "--json"],
                             capture_output=True, text=True, encoding="utf-8", timeout=20, check=False)
        data: Any = json.loads(run.stdout) if run.stdout.strip() else {"raw": run.stderr.strip()}
        return {"status": "ok" if run.returncode == 0 else "warning", "result": data}
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        return {"status": "warning", "result": {"error": "%s: %s" % (type(exc).__name__, exc)}}


def _setup_environment() -> dict[str, Any]:
    """既存 setup の環境確認をそのまま集約する。 / Reuse the setup environment probe as the diagnostic core."""
    try:
        from fullseye import setup_cmd
        return {"status": "ok", "result": setup_cmd.collect_env()}
    except Exception as exc:  # noqa: BLE001 - doctor reports an unavailable probe instead of crashing
        return {"status": "warning", "result": {"error": "%s: %s" % (type(exc).__name__, exc)}}


def collect(*, env: Optional[dict[str, str]] = None, executable: Optional[str] = None,
            platform: Optional[str] = None, include_sdk: bool = True) -> dict[str, Any]:
    """現在のプロセスを変更せずに診断結果を集める。 / Collect non-mutating diagnostic facts.

    ``env`` / ``executable`` / ``platform`` are injection points for deterministic tests;
    they never cause a real registry, package, or network write.
    """
    environment = dict(os.environ if env is None else env)
    exe = executable or sys.executable
    context = {"platform": platform or sys.platform, "env": environment, "executable": exe}
    windows = _is_windows(context)
    findings: list[dict[str, Any]] = []
    encoding = (getattr(sys.stdout, "encoding", None) or "").lower()
    cp932 = encoding in {"cp932", "ms932", "shift_jis", "shift-jis"}
    findings.append(_item(
        "console_encoding", "warning" if cp932 else "ok", "Console text encoding",
        "stdout encoding is %s" % (encoding or "unknown"),
        "Run this PowerShell command before Fullseye; it avoids cp932 UnicodeEncodeError.",
        ("chcp 65001; $env:PYTHONUTF8='1'",) if cp932 else (),
    ))
    long_paths = _read_long_paths() if windows and platform is None else None
    status = "warning" if long_paths is False else ("ok" if long_paths else "manual")
    findings.append(_item(
        "long_path", status, "Windows long-path support",
        "LongPathsEnabled=%s" % ("1" if long_paths else "0" if long_paths is False else "not read"),
        "Enable Win32 long paths, then restart Windows; keep projects near C:\\src until then.",
        ("Start-Process powershell -Verb RunAs",) if long_paths is False else (),
    ))
    non_ascii = not _is_ascii_path(exe)
    has_space = " " in exe
    findings.append(_item(
        "unicode_space_path", "info" if non_ascii or has_space else "ok", "Unicode or spaces in paths",
        "Python path: %s" % exe,
        "Quote every path. If a third-party native tool still fails, make a venv at C:\\venvs\\fullseye.",
        (_command(exe, "-m", "venv", r"C:\\venvs\\fullseye"),) if non_ascii or has_space else (),
    ))
    redirected, redirected_paths = _windows_known_folder_env(environment) if windows else (False, "")
    findings.append(_item(
        "onedrive_known_folders", "info" if redirected else "ok", "OneDrive known-folder redirection",
        "OneDrive path detected: %s" % (redirected_paths or "no"),
        "Keep projects and data outside synced Desktop/Documents, then relink files in Studio.",
        ("New-Item -ItemType Directory -Force C:\\src, C:\\data",) if redirected else (),
    ))
    store = "windowsapps" in exe.lower() or "microsoft" in exe.lower() and "python" in exe.lower()
    findings.append(_item(
        "store_python", "warning" if store else "ok", "Microsoft Store Python",
        "Python executable: %s" % exe,
        "Use python.org Python or a venv; Store Python can redirect APPDATA and deny setup writes.",
        ("py -3.11 -m venv $HOME\\venvs\\fullseye",) if store else (),
    ))
    conda = bool(environment.get("CONDA_PREFIX")) or "conda" in exe.lower()
    pythonw = exe.lower().endswith("pythonw.exe")
    findings.append(_item(
        "conda_pythonw", "warning" if conda and pythonw else ("info" if conda else "ok"),
        "conda / pythonw DLL environment", "CONDA_PREFIX=%s; executable=%s" %
        (environment.get("CONDA_PREFIX", "unset"), exe),
        "Activate the conda environment before starting Studio; do not launch its pythonw.exe directly.",
        ("conda activate <environment>; fullseye-studio",) if conda else (),
    ))
    path_sep = ";" if windows else os.pathsep
    path_parts = [p for p in environment.get("PATH", "").split(path_sep) if p]
    exe_dir = (exe.rsplit("\\", 1)[0] if windows and "\\" in exe else os.path.dirname(exe))
    has_python_dir = exe_dir in path_parts
    command_names = ("python.exe", "py.exe", "python", "py") if windows else ("python", "python3")
    has_python_command = any((Path(folder) / name).is_file() for folder in path_parts for name in command_names)
    findings.append(_item(
        "python_path", "ok" if has_python_command else "warning",
        "Python command on PATH", "python/py found=%s; current Python directory on PATH=%s" %
        (has_python_command, has_python_dir),
        "Use the current interpreter explicitly; activation is optional.",
        (_command(exe, "-m", "fullseye", "doctor"),),
    ))
    names = [p for p in path_parts if Path(p).name.lower() in {"scripts", "bin"} or "python" in p.lower()]
    findings.append(_item(
        "multiple_python", "info" if len(names) > 2 else "ok", "Multiple Python installations",
        "PATH has %d Python-like entries" % len(names),
        "Install and run with one interpreter: <python> -m pip ... then <python> -m fullseye ...",
        (_command(exe, "-m", "pip", "--version"),),
    ))
    root = _distribution_root()
    imported = Path(__file__).resolve().parents[1]
    mismatch = root is not None and imported not in (root, *root.parents)
    findings.append(_item(
        "pip_target", "warning" if mismatch else "ok", "pip target matches imported Fullseye",
        "imported=%s; distribution=%s" % (imported, root or "not installed"),
        "Use this exact Python for pip, then verify the imported copy.",
        (_command(exe, "-m", "pip", "install", "--upgrade", "fullseye"),
         _command(exe, "-c", "import fullseye; print(fullseye.__file__)")),
    ))
    qt_spec = importlib.util.find_spec("PySide6")
    plugin_path = environment.get("QT_PLUGIN_PATH", "")
    native_status = "warning" if plugin_path and not Path(plugin_path).exists() else "ok"
    findings.append(_item(
        "native_dll", native_status, "Native DLL and Qt plugin loading",
        "PySide6=%s; QT_PLUGIN_PATH=%s" % ("found" if qt_spec else "not installed", plugin_path or "unset"),
        "Install the matching package with this Python. For DLL errors install Microsoft Visual C++ 2015-2022 x64,"
        " then run doctor again.",
        (_command(exe, "-m", "pip", "install", "--upgrade", '"fullseye[gui]"'),
         "winget install Microsoft.VCRedist.2015+.x64") if qt_spec or plugin_path else (),
        fixable=bool(sys.platform == "win32" and plugin_path and not Path(plugin_path).exists()),
    ))
    findings.append(_item(
        "antivirus_lock", "manual", "Antivirus lock or quarantine", "No safe read-only quarantine API is portable.",
        "Restore only the Fullseye file after checking its publisher; exclude the venv/project, not all of Python.",
        ("Get-MpThreatDetection",) if windows else (),
    ))
    policy = environment.get("PSExecutionPolicy", "not queried")
    findings.append(_item(
        "powershell_policy", "info" if windows and policy != "not queried" else "manual",
        "PowerShell execution policy", "PSExecutionPolicy=%s" % policy,
        "For a local signed installer, inspect first, then use a process-only policy; do not lower machine-wide policy.",
        ("Get-ExecutionPolicy -List", "Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned") if windows else (),
    ))
    proxy = any(environment.get(k) for k in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"))
    findings.append(_item(
        "proxy_certificate", "info" if proxy else "ok", "Corporate proxy and TLS certificates",
        "proxy configured=%s; default CA paths=%s" % (proxy, bool(ssl.get_default_verify_paths().cafile)),
        "Ask IT for the corporate root certificate; set REQUESTS_CA_BUNDLE to that PEM instead of disabling TLS checks.",
        ("$env:REQUESTS_CA_BUNDLE='C:\\certs\\company-root.pem'",) if proxy else (),
    ))
    in_program_files = windows and "program files" in exe.lower()
    findings.append(_item(
        "write_permission", "warning" if in_program_files else "ok", "Write permission / Program Files install",
        "Python under Program Files=%s" % in_program_files,
        "Use a user venv; do not run pip or Studio as Administrator just to bypass a protected installation.",
        (_command(exe, "-m", "venv", "%USERPROFILE%\\venvs\\fullseye"),) if in_program_files else (),
    ))
    dpi = environment.get("FULLSEYE_DPI_SCALE", "not queried")
    findings.append(_item(
        "high_dpi", "info" if dpi not in ("not queried", "100", "1", "1.0") else "manual",
        "High-DPI scaling", "DPI scale=%s" % dpi,
        "Set Windows Settings > Display > Scale to 100% for a comparison, then restart Studio; keep the value that is readable.",
    ))
    torch = importlib.util.find_spec("torch")
    cuda_visible = environment.get("CUDA_VISIBLE_DEVICES", "")
    findings.append(_item(
        "cuda_driver", "info" if torch else "ok", "GPU driver / CUDA compatibility",
        "torch=%s; CUDA_VISIBLE_DEVICES=%s" % ("found" if torch else "not installed", cuda_visible or "unset"),
        "Use the driver supported by the installed torch CUDA build, or use CPU; never mix an arbitrary CUDA toolkit into the venv.",
        ("nvidia-smi", _command(exe, "-c", "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())")) if torch else (),
    ))
    zone = exe + ":Zone.Identifier"
    findings.append(_item(
        "smartscreen", "manual" if windows else "ok", "Defender SmartScreen / downloaded-file mark",
        "Zone.Identifier checked=%s" % ("not read" if windows else "not applicable"),
        "Verify the download's source and hash, then use Properties > Unblock for that file only; do not disable SmartScreen.",
        ("Get-Item -Stream Zone.Identifier <downloaded-file>",) if windows else (),
    ))
    result: dict[str, Any] = {"schema": 1, "python": {"executable": exe, "version": sys.version.split()[0]},
                              "findings": findings, "setup_environment": _setup_environment()}
    if include_sdk:
        result["sdk"] = _sdk_doctor()
    return result


def _has_failures(report: dict[str, Any]) -> bool:
    return any(f["status"] == "warning" for f in report["findings"])


def format_report(report: dict[str, Any]) -> str:
    """例外を隠さず、各結果に確認値と貼り付け可能な修復を出す。 / Render facts and repairs."""
    lines = ["Fullseye doctor", "Python: %s (%s)" % (report["python"]["version"], report["python"]["executable"])]
    for finding in report["findings"]:
        tag = {"ok": "OK", "warning": "ACTION", "info": "NOTE", "manual": "CHECK"}[finding["status"]]
        lines += ["", "[%s] %s — %s" % (tag, finding["id"], finding["what"]),
                  "  Checked: %s" % finding["checked"]]
        if finding["status"] != "ok":
            lines.append("  Fix: %s" % finding["fix"])
            lines.extend("  PowerShell: %s" % cmd for cmd in finding["commands"])
    if report.get("sdk") is not None:
        lines += ["", "[SDK] delegated doctor: %s" % report["sdk"]["status"]]
    lines += ["", "[SETUP] environment probe: %s" % report["setup_environment"]["status"]]
    lines += ["", "Run again after a repair: %s" % _command(sys.executable, "-m", "fullseye", "doctor")]
    return "\n".join(lines) + "\n"


def _fix_plan(report: dict[str, Any]) -> list[dict[str, Any]]:
    """現在は壊れた QT_PLUGIN_PATH だけを可逆に消せる。 / List only reversible fixes."""
    return [f for f in report["findings"] if f["id"] == "native_dll" and f["fixable"]]


def _apply_fixes(plan: Iterable[dict[str, Any]]) -> list[str]:
    changed: list[str] = []
    for finding in plan:
        if finding["id"] == "native_dll":
            os.environ.pop("QT_PLUGIN_PATH", None)
            powershell = Path(os.environ.get("SystemRoot", r"C:\\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
            if not powershell.is_file():
                raise OSError("Windows PowerShell was not found at %s" % powershell)
            subprocess.run([str(powershell), "-NoProfile", "-Command",
                            "[Environment]::SetEnvironmentVariable('QT_PLUGIN_PATH', $null, 'User')"],
                           check=True, capture_output=True, text=True, timeout=20)
            changed.append("removed stale QT_PLUGIN_PATH from this process and the user environment")
    return changed


def main(argv: Optional[Sequence[str]] = None, *, collect_fn: Callable[[], dict[str, Any]] = collect,
         input_fn: Callable[[str], str] = input, is_tty: Optional[bool] = None,
         apply_fn: Callable[[Iterable[dict[str, Any]]], list[str]] = _apply_fixes, out=None) -> int:
    """CLI entry: ``--json`` for tools and conservative ``--fix`` for terminals. / CLI with fail-closed fixing."""
    ap = argparse.ArgumentParser(prog="fullseye doctor", description="Diagnose Fullseye startup problems without changing the system.")
    ap.add_argument("--json", action="store_true", help="print machine-readable diagnostics")
    ap.add_argument("--fix", action="store_true", help="show and confirm safe, reversible repairs")
    ap.add_argument("--yes", action="store_true", help="confirm --fix (ignored without a terminal)")
    args = ap.parse_args(list(argv) if argv is not None else None)
    out = out or sys.stdout
    report = collect_fn()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), file=out)
    else:
        print(format_report(report), end="", file=out)
    if not args.fix:
        return 1 if _has_failures(report) else 0
    if is_tty is None:
        try:
            from fullseye.setup_cmd import _stdin_is_terminal
            is_tty = _stdin_is_terminal()
        except Exception:  # noqa: BLE001 - a failed terminal probe must never permit a fix
            is_tty = False
    plan = _fix_plan(report)
    if not plan:
        print("No safe automatic repair is available; use the commands above.", file=out)
        return 1 if _has_failures(report) else 0
    print("Planned change: remove the stale per-user QT_PLUGIN_PATH because it names a missing directory.", file=out)
    if not is_tty:
        print("No terminal detected: --fix made no changes. Run in a terminal and confirm.", file=out)
        return 1
    confirmed = args.yes or input_fn("Apply this change? [y/N] ").strip().lower() in {"y", "yes"}
    if not confirmed:
        print("No changes made.", file=out)
        return 1
    try:
        messages = apply_fn(plan)
    except (OSError, subprocess.SubprocessError) as exc:
        print("No change completed: %s: %s" % (type(exc).__name__, exc), file=out)
        return 1
    for message in messages:
        print("Changed: %s" % message, file=out)
    return 0
