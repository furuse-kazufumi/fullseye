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
import io
import importlib.metadata
import importlib.util
import json
import os
import shlex
import shutil
import ssl
import subprocess
import sys
import tempfile
from dataclasses import dataclass
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


@dataclass(frozen=True)
class Command:
    """PowerShell / bash の生の argv。表示時までエスケープしない。 / Raw argv for both shells, escaped only at display time.

    ``*_script`` is only for shell grammar such as ``&&`` that cannot be an argv
    element. / ``*_script`` は argv にできない ``&&`` 等の shell 構文だけに使う。
    """

    powershell: tuple[str, ...]
    bash: tuple[str, ...]
    powershell_script: Optional[str] = None
    bash_script: Optional[str] = None


def _argv(*parts: str) -> Command:
    """両方の shell で同じ argv を使う命令。 / A command with the same argv in both shells."""
    return Command(tuple(parts), tuple(parts))


def _shell(powershell: Sequence[str], bash: Sequence[str]) -> Command:
    """shell ごとに構文が違う命令を表す。 / Describe a command whose shell syntax differs."""
    return Command(tuple(powershell), tuple(bash))


def _script(powershell: str, bash: str) -> Command:
    """shell の区切りを含む命令を、意図どおり表示する。 / Keep shell separators outside argv."""
    return Command((), (), powershell_script=powershell, bash_script=bash)


def _quote_powershell(part: str) -> str:
    """PowerShell の 1 引数を貼り付け可能にする。 / Make one PowerShell argument pasteable.

    Windows paths keep one literal backslash.  They are quoted only when they contain
    whitespace; a double-quoted token also protects PowerShell metacharacters there.
    """
    if not any(c.isspace() for c in part):
        return part
    return '"%s"' % part.replace("`", "``").replace('"', '`"').replace("$", "`$")


def _quote_bash(part: str) -> str:
    """bash の 1 引数を貼り付け可能にする。 / Make one bash argument pasteable."""
    if part.startswith("$HOME/"):
        return '"$HOME"' + part[len("$HOME"):]
    return shlex.quote(part)


def _render_command(command: Command) -> dict[str, str]:
    """表示の直前に一か所だけで shell 用にエスケープする。 / Escape commands in one place, immediately before display."""
    powershell = command.powershell_script or " ".join(_quote_powershell(part) for part in command.powershell)
    # 空白を含む実行ファイルは call operator が必要。無いと ScriptBlock は引用パスをコマンドでなく文字列式として読む。
    # A quoted executable needs PowerShell's call operator; otherwise ScriptBlock
    # parses the quoted path as a string expression instead of a command invocation.
    if command.powershell and any(c.isspace() for c in command.powershell[0]):
        powershell = "& " + powershell
    return {
        "powershell": powershell,
        "bash": command.bash_script or " ".join(_quote_bash(part) for part in command.bash),
    }


def _repair_commands(exe: str) -> dict[str, tuple[Command, ...]]:
    """各診断の貼り付け命令。文字列の quoting はここでは決してしない。 / Repair argv for every finding; quoting is deliberately deferred."""
    return {
        "console_encoding": (_shell(("chcp", "65001;", "$env:PYTHONUTF8='1'"),
                                     ("export", "PYTHONUTF8=1")),),
        "long_path": (_shell(("Start-Process", "powershell", "-Verb", "RunAs"),
                              ("powershell.exe", "-NoProfile", "-Command", "Start-Process powershell -Verb RunAs")),),
        "unicode_space_path": (_argv(exe, "-m", "venv", r"C:\venvs\fullseye"),),
        "onedrive_known_folders": (_shell(("New-Item", "-ItemType", "Directory", "-Force", r"C:\src,", r"C:\data"),
                                            ("mkdir", "-p", "/c/src", "/c/data")),),
        "store_python": (_shell(("py", "-3.11", "-m", "venv", r"$HOME\venvs\fullseye"),
                                  ("py", "-3.11", "-m", "venv", "$HOME/venvs/fullseye")),),
        "conda_pythonw": (_script("conda activate fullseye; fullseye-studio",
                                   "conda activate fullseye && fullseye-studio"),),
        "python_path": (_argv(exe, "-m", "fullseye", "doctor"),),
        "multiple_python": (_argv(exe, "-m", "pip", "--version"),),
        "pip_target": (_argv(exe, "-m", "pip", "install", "--upgrade", "fullseye"),
                       _argv(exe, "-c", "import fullseye; print(fullseye.__file__)")),
        "native_dll": (_argv(exe, "-m", "pip", "install", "--upgrade", "fullseye[gui]"),
                       _argv("winget", "install", "Microsoft.VCRedist.2015+.x64")),
        "antivirus_lock": (_shell(("Get-MpThreatDetection",),
                                   ("powershell.exe", "-NoProfile", "-Command", "Get-MpThreatDetection")),),
        "powershell_policy": (_shell(("Get-ExecutionPolicy", "-List"),
                                      ("powershell.exe", "-NoProfile", "-Command", "Get-ExecutionPolicy -List")),
                              _shell(("Set-ExecutionPolicy", "-Scope", "Process", "-ExecutionPolicy", "RemoteSigned"),
                                     ("powershell.exe", "-NoProfile", "-Command", "Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned"))),
        "proxy_certificate": (_shell((r"$env:REQUESTS_CA_BUNDLE='C:\certs\company-root.pem'",),
                                      ("export", "REQUESTS_CA_BUNDLE=/c/certs/company-root.pem")),),
        "write_permission": (_shell(("py", "-3.11", "-m", "venv", r"$HOME\venvs\fullseye"),
                                      ("py", "-3.11", "-m", "venv", "$HOME/venvs/fullseye")),),
        "cuda_driver": (_argv("nvidia-smi"),
                        _argv(exe, "-c", "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())")),
        "smartscreen": (_shell(("Get-Item", "-LiteralPath", r"C:\path\to\downloaded-file", "-Stream", "Zone.Identifier"),
                                ("powershell.exe", "-NoProfile", "-Command", "Get-Item -LiteralPath 'C:\\path\\to\\downloaded-file' -Stream Zone.Identifier")),),
    }


def _item(
    ident: str, status: str, what: str, checked: str, fix: str,
    commands: Sequence[Command] = (), *, detail: str = "", fixable: bool = False,
) -> dict[str, Any]:
    """診断 1 件を JSON と人間向け表示で共有する形にする。 / Make one shared text/JSON finding."""
    return {"id": ident, "status": status, "what": what, "checked": checked,
            "detail": detail, "fix": fix, "command_specs": list(commands), "fixable": fixable}


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


def _qt_plugin_entries(value: str) -> list[str]:
    """QT_PLUGIN_PATH を Windows の ``;`` 単位で保つ。 / Preserve QT_PLUGIN_PATH entries split by Windows ``;``."""
    return [entry for entry in value.split(";") if entry]


def _stale_qt_plugin_entries(value: str) -> list[str]:
    """実在しない Qt plugin folder だけを返す。 / Return only Qt plugin folders confirmed missing."""
    return [entry for entry in _qt_plugin_entries(value) if not Path(entry).is_dir()]


def _remove_qt_plugin_entries(value: str, stale: Iterable[str]) -> str:
    """確認済みの古い項目だけを除く。 / Remove only entries already confirmed stale."""
    stale_keys = {os.path.normcase(entry) for entry in stale}
    return ";".join(entry for entry in _qt_plugin_entries(value)
                    if os.path.normcase(entry) not in stale_keys)


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
    commands = _repair_commands(exe)
    context = {"platform": platform or sys.platform, "env": environment, "executable": exe}
    windows = _is_windows(context)
    findings: list[dict[str, Any]] = []
    encoding = (getattr(sys.stdout, "encoding", None) or "").lower()
    cp932 = encoding in {"cp932", "ms932", "shift_jis", "shift-jis"}
    findings.append(_item(
        "console_encoding", "warning" if cp932 else "ok", "Console text encoding",
        "stdout encoding is %s" % (encoding or "unknown"),
        "Run this PowerShell command before Fullseye; it avoids cp932 UnicodeEncodeError.",
        commands["console_encoding"] if cp932 else (),
    ))
    long_paths = _read_long_paths() if windows and platform is None else None
    status = "warning" if long_paths is False else ("ok" if long_paths else "manual")
    findings.append(_item(
        "long_path", status, "Windows long-path support",
        "LongPathsEnabled=%s" % ("1" if long_paths else "0" if long_paths is False else "not read"),
        "Enable Win32 long paths, then restart Windows; keep projects near C:\\src until then.",
        commands["long_path"] if long_paths is False else (),
    ))
    non_ascii = not _is_ascii_path(exe)
    has_space = " " in exe
    findings.append(_item(
        "unicode_space_path", "info" if non_ascii or has_space else "ok", "Unicode or spaces in paths",
        "Python path: %s" % exe,
        "Quote every path. If a third-party native tool still fails, make a venv at C:\\venvs\\fullseye.",
        commands["unicode_space_path"] if non_ascii or has_space else (),
    ))
    redirected, redirected_paths = _windows_known_folder_env(environment) if windows else (False, "")
    findings.append(_item(
        "onedrive_known_folders", "info" if redirected else "ok", "OneDrive known-folder redirection",
        "OneDrive path detected: %s" % (redirected_paths or "no"),
        "Keep projects and data outside synced Desktop/Documents, then relink files in Studio.",
        commands["onedrive_known_folders"] if redirected else (),
    ))
    store = "windowsapps" in exe.lower() or "microsoft" in exe.lower() and "python" in exe.lower()
    findings.append(_item(
        "store_python", "warning" if store else "ok", "Microsoft Store Python",
        "Python executable: %s" % exe,
        "Use python.org Python or a venv; Store Python can redirect APPDATA and deny setup writes.",
        commands["store_python"] if store else (),
    ))
    conda = bool(environment.get("CONDA_PREFIX")) or "conda" in exe.lower()
    pythonw = exe.lower().endswith("pythonw.exe")
    findings.append(_item(
        "conda_pythonw", "warning" if conda and pythonw else ("info" if conda else "ok"),
        "conda / pythonw DLL environment", "CONDA_PREFIX=%s; executable=%s" %
        (environment.get("CONDA_PREFIX", "unset"), exe),
        "Activate the conda environment before starting Studio; do not launch its pythonw.exe directly.",
        commands["conda_pythonw"] if conda else (),
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
        commands["python_path"],
    ))
    names = [p for p in path_parts if Path(p).name.lower() in {"scripts", "bin"} or "python" in p.lower()]
    findings.append(_item(
        "multiple_python", "info" if len(names) > 2 else "ok", "Multiple Python installations",
        "PATH has %d Python-like entries" % len(names),
        "Install and run with one interpreter: <python> -m pip ... then <python> -m fullseye ...",
        commands["multiple_python"],
    ))
    root = _distribution_root()
    imported = Path(__file__).resolve().parents[1]
    mismatch = root is not None and imported not in (root, *root.parents)
    findings.append(_item(
        "pip_target", "warning" if mismatch else "ok", "pip target matches imported Fullseye",
        "imported=%s; distribution=%s" % (imported, root or "not installed"),
        "Use this exact Python for pip, then verify the imported copy.",
        commands["pip_target"],
    ))
    qt_spec = importlib.util.find_spec("PySide6")
    plugin_path = environment.get("QT_PLUGIN_PATH", "")
    stale_plugin_paths = _stale_qt_plugin_entries(plugin_path)
    native_status = "warning" if stale_plugin_paths else "ok"
    native = _item(
        "native_dll", native_status, "Native DLL and Qt plugin loading",
        "PySide6=%s; stale QT_PLUGIN_PATH entries=%s" %
        ("found" if qt_spec else "not installed", "; ".join(stale_plugin_paths) or "none"),
        "Install the matching package with this Python. For DLL errors install Microsoft Visual C++ 2015-2022 x64,"
        " then run doctor again.",
        commands["native_dll"] if qt_spec or plugin_path else (),
        fixable=bool(sys.platform == "win32" and stale_plugin_paths),
    )
    native["stale_qt_plugin_paths"] = stale_plugin_paths
    findings.append(native)
    findings.append(_item(
        "antivirus_lock", "manual", "Antivirus lock or quarantine", "No safe read-only quarantine API is portable.",
        "Restore only the Fullseye file after checking its publisher; exclude the venv/project, not all of Python.",
        commands["antivirus_lock"] if windows else (),
    ))
    policy = environment.get("PSExecutionPolicy", "not queried")
    findings.append(_item(
        "powershell_policy", "info" if windows and policy != "not queried" else "manual",
        "PowerShell execution policy", "PSExecutionPolicy=%s" % policy,
        "For a local signed installer, inspect first, then use a process-only policy; do not lower machine-wide policy.",
        commands["powershell_policy"] if windows else (),
    ))
    proxy = any(environment.get(k) for k in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"))
    findings.append(_item(
        "proxy_certificate", "info" if proxy else "ok", "Corporate proxy and TLS certificates",
        "proxy configured=%s; default CA paths=%s" % (proxy, bool(ssl.get_default_verify_paths().cafile)),
        "Ask IT for the corporate root certificate; set REQUESTS_CA_BUNDLE to that PEM instead of disabling TLS checks.",
        commands["proxy_certificate"] if proxy else (),
    ))
    in_program_files = windows and "program files" in exe.lower()
    findings.append(_item(
        "write_permission", "warning" if in_program_files else "ok", "Write permission / Program Files install",
        "Python under Program Files=%s" % in_program_files,
        "Use a user venv; do not run pip or Studio as Administrator just to bypass a protected installation.",
        commands["write_permission"] if in_program_files else (),
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
        commands["cuda_driver"] if torch else (),
    ))
    zone = exe + ":Zone.Identifier"
    findings.append(_item(
        "smartscreen", "manual" if windows else "ok", "Defender SmartScreen / downloaded-file mark",
        "Zone.Identifier checked=%s" % ("not read" if windows else "not applicable"),
        "Verify the download's source and hash, then use Properties > Unblock for that file only; do not disable SmartScreen.",
        commands["smartscreen"] if windows else (),
    ))
    result: dict[str, Any] = {"schema": 1, "python": {"executable": exe, "version": sys.version.split()[0]},
                              "findings": findings, "setup_environment": _setup_environment()}
    if include_sdk:
        result["sdk"] = _sdk_doctor()
    return result


def _has_failures(report: dict[str, Any]) -> bool:
    return any(f["status"] == "warning" for f in report["findings"])


_EN_FIX = {
    "console_encoding": "chcp 65001; $env:PYTHONUTF8='1' in the same PowerShell",
    "long_path": "Enable Windows long paths as Administrator and reboot; meanwhile use a short root such as C:\\src",
    "unicode_space_path": "Quote paths as \"...\"; for an old DLL that still fails, make the venv at C:\\venvs\\fullseye",
    "onedrive_known_folders": "New-Item -ItemType Directory -Force C:\\src, C:\\data; move projects/data there and reselect them in Studio",
    "store_python": "Use python.org Python or a venv: py -3.11 -m venv $HOME\\venvs\\fullseye",
    "conda_pythonw": "conda activate fullseye; fullseye-studio; do not double-click pythonw.exe",
    "python_path": "Use py -3.11 -m fullseye doctor, or activate the venv",
    "multiple_python": "Use the same <python> -m pip install ... and <python> -m fullseye ...",
    "pip_target": "With the shown Python run <python> -m pip install --upgrade fullseye, then <python> -c \"import fullseye; print(fullseye.__file__)\"",
    "native_dll": "<python> -m pip install --upgrade fullseye[gui]; install VC++ 2015–2022 x64: winget install Microsoft.VCRedist.2015+.x64; follow SDK doctor for python3XX.dll",
    "antivirus_lock": "Verify source/hash, then restore/exclude only the Fullseye venv/project; never exclude all Python",
    "powershell_policy": "Inspect first, then only for this process: Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned",
    "proxy_certificate": "Obtain the PEM from IT and set $env:REQUESTS_CA_BUNDLE='C:\\certs\\company-root.pem'; do not routinely disable TLS",
    "write_permission": "Use a user venv, not Administrator: py -3.11 -m venv $HOME\\venvs\\fullseye",
    "high_dpi": "Test Settings > System > Display > Scale at 100%, restart Studio, then keep the readable value",
    "cuda_driver": "Update to a supported NVIDIA driver or use CPU; do not mix an arbitrary CUDA toolkit into the venv",
    "smartscreen": "Verify source and hash, then use Properties > Unblock for that file only; do not disable SmartScreen",
}


_JA_TEXT = {
    "console_encoding": ("コンソールの文字エンコーディング", "chcp 65001; $env:PYTHONUTF8='1' を同じ PowerShell で実行"),
    "long_path": ("Windows の長いパスの対応", "管理者で Windows の「長いパスを有効にする」を有効化して再起動。急ぎなら C:\\src のような短い場所へ置く"),
    "unicode_space_path": ("パス中の日本語または空白", "パスを常に \"...\" で引用。直らない古い DLL は C:\\venvs\\fullseye に venv を作る"),
    "onedrive_known_folders": ("OneDrive の既知フォルダー移動", "New-Item -ItemType Directory -Force C:\\src, C:\\data、プロジェクトと大量データはそこへ移して Studio で再選択"),
    "store_python": ("Microsoft Store Python", "python.org 版 Python か venv を使用: py -3.11 -m venv $HOME\\venvs\\fullseye"),
    "conda_pythonw": ("conda / pythonw の DLL 環境", "conda activate fullseye; fullseye-studio。pythonw.exe を直接ダブルクリックしない"),
    "python_path": ("PATH 上の Python コマンド", "py -3.11 -m fullseye doctor のように Python を明示、または venv を activate"),
    "multiple_python": ("複数の Python インストール", "常に同じ <python> -m pip install ... と <python> -m fullseye ... を使う"),
    "pip_target": ("pip の配布先と読み込んだ Fullseye の一致", "doctor が示す Python で <python> -m pip install --upgrade fullseye、続けて <python> -c \"import fullseye; print(fullseye.__file__)\""),
    "native_dll": ("ネイティブ DLL と Qt plugin の読み込み", "<python> -m pip install --upgrade fullseye[gui]。VC++ 2015–2022 x64 を入れる: winget install Microsoft.VCRedist.2015+.x64。SDK の python3XX.dll は SDK doctor の指示に従う"),
    "antivirus_lock": ("ウイルス対策ソフトによるロックまたは隔離", "出所・ハッシュを確認後、Fullseye の venv/プロジェクトだけを復元・除外。Python 全体を除外しない"),
    "powershell_policy": ("PowerShell の実行ポリシー", "内容を確認後、現在のプロセスだけ Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned。全体のポリシーは下げない"),
    "proxy_certificate": ("社内 proxy と TLS 証明書", "IT から PEM を受け $env:REQUESTS_CA_BUNDLE='C:\\certs\\company-root.pem'。--trusted-host や TLS 無効化を常用しない"),
    "write_permission": ("書き込み権限 / Program Files へのインストール", "管理者でなくユーザー venv を作る: py -3.11 -m venv $HOME\\venvs\\fullseye"),
    "high_dpi": ("高 DPI の拡大縮小", "Windows 設定 > システム > ディスプレイ > 拡大縮小を 100% でも一度確認し、Studio を再起動。読みやすい倍率を採用"),
    "cuda_driver": ("GPU driver / CUDA の互換性", "対応する NVIDIA driver に更新、または CPU を使う。任意の CUDA toolkit を venv に混ぜない"),
    "smartscreen": ("Defender SmartScreen / ダウンロード済みファイルの印", "出所とハッシュを検証後、そのファイルだけ プロパティ > 許可する。SmartScreen は無効化しない"),
}


def _detect_lang(override: Optional[str] = None) -> str:
    """setup と同じ優先順位で ja / en を決める。 / Use setup's language precedence unchanged."""
    from fullseye.setup_cmd import detect_lang
    return detect_lang(override=override)


def _checked_text(finding: dict[str, Any], lang: str) -> str:
    """観測値を訳すが、測定した値そのものは変えない。 / Translate labels without changing measured values."""
    if lang == "en":
        return finding["checked"]
    value = finding["checked"]
    ident = finding["id"]
    prefix = {
        "console_encoding": "標準出力の文字エンコーディング: ",
        "long_path": "LongPathsEnabled=",
        "unicode_space_path": "Python のパス: ",
        "onedrive_known_folders": "検出した OneDrive のパス: ",
        "store_python": "Python 実行ファイル: ",
        "conda_pythonw": "",
        "python_path": "",
        "multiple_python": "PATH 内の Python らしい項目数: ",
        "pip_target": "",
        "native_dll": "",
        "antivirus_lock": "安全に読める隔離情報 API はありません。",
        "powershell_policy": "PSExecutionPolicy=",
        "proxy_certificate": "",
        "write_permission": "Python が Program Files の下か: ",
        "high_dpi": "DPI scale=",
        "cuda_driver": "",
        "smartscreen": "Zone.Identifier の確認: ",
    }[ident]
    if ident == "console_encoding":
        return prefix + value.removeprefix("stdout encoding is ")
    if ident == "long_path":
        return prefix + value.removeprefix("LongPathsEnabled=")
    if ident in {"unicode_space_path", "store_python"}:
        return prefix + value.split(": ", 1)[-1]
    if ident == "onedrive_known_folders":
        return prefix + value.removeprefix("OneDrive path detected: ")
    if ident == "conda_pythonw":
        return "CONDA_PREFIX=" + value.removeprefix("CONDA_PREFIX=").replace("; executable=", "; 実行ファイル=")
    if ident == "python_path":
        return "python/py を検出=%s; 現在の Python のフォルダーが PATH 上=%s" % tuple(
            part.split("=", 1)[-1] for part in value.split("; "))
    if ident == "multiple_python":
        return prefix + value.split(" ")[2]
    if ident == "pip_target":
        return "読み込み元=" + value.removeprefix("imported=").replace("; distribution=", "; 配布先=")
    if ident == "native_dll":
        return value.replace("found", "検出").replace("not installed", "未導入").replace("unset", "未設定")
    if ident == "antivirus_lock":
        return prefix
    if ident == "powershell_policy":
        return prefix + value.removeprefix("PSExecutionPolicy=")
    if ident == "proxy_certificate":
        return value.replace("proxy configured=", "proxy を設定=").replace("; default CA paths=", "; 既定 CA パス=")
    if ident == "write_permission":
        return prefix + value.removeprefix("Python under Program Files=")
    if ident == "high_dpi":
        return prefix + value.removeprefix("DPI scale=")
    if ident == "cuda_driver":
        return value.replace("found", "検出").replace("not installed", "未導入").replace("unset", "未設定")
    if ident == "smartscreen":
        return prefix + value.removeprefix("Zone.Identifier checked=").replace("not read", "未確認")
    return value


def _present_finding(finding: dict[str, Any], lang: str) -> dict[str, Any]:
    """表示用の訳文と shell 別の命令を作る。 / Prepare translated display text and shell-specific commands."""
    shown = {key: value for key, value in finding.items() if key != "command_specs"}
    if lang == "ja":
        shown["what"], shown["fix"] = _JA_TEXT[finding["id"]]
    else:
        shown["fix"] = _EN_FIX[finding["id"]]
    shown["checked"] = _checked_text(finding, lang)
    shown["commands"] = [_render_command(command) for command in finding["command_specs"]]
    return shown


def _summary(report: dict[str, Any], lang: str) -> str:
    """最初に読む 1 行の実測件数。 / The measured one-line result at the top of the report."""
    counts = {status: sum(f["status"] == status for f in report["findings"])
              for status in ("warning", "info", "manual", "ok")}
    checks = counts["info"] + counts["manual"]
    if lang == "ja":
        return "問題 %d 件・確認のお願い %d 件・OK %d 件。まず [ACTION] から。" % (counts["warning"], checks, counts["ok"])
    return "%d issue(s) · %d item(s) to check · %d OK. Start with [ACTION]." % (counts["warning"], checks, counts["ok"])


def _present_report(report: dict[str, Any], lang: str) -> dict[str, Any]:
    """JSON も人間向け表示と同じ訳文・命令を返す。 / Make JSON use the same translated text and commands as the terminal."""
    shown = {key: value for key, value in report.items() if key != "findings"}
    shown["summary"] = _summary(report, lang)
    shown["findings"] = [_present_finding(finding, lang) for finding in report["findings"]]
    return shown


def format_report(report: dict[str, Any], lang: str = "en") -> str:
    """例外を隠さず、各結果に確認値と貼り付け可能な修復を出す。 / Render facts and repairs."""
    shown = _present_report(report, lang)
    labels = {"ja": {"checked": "確認した値", "fix": "対処", "again": "修復後にもう一度実行:"},
              "en": {"checked": "Checked", "fix": "Fix", "again": "Run again after a repair:"}}[lang]
    lines = [shown["summary"], "Fullseye doctor", "Python: %s (%s)" %
             (shown["python"]["version"], shown["python"]["executable"])]
    for finding in shown["findings"]:
        tag = {"ok": "OK", "warning": "ACTION", "info": "NOTE", "manual": "CHECK"}[finding["status"]]
        lines += ["", "[%s] %s — %s" % (tag, finding["id"], finding["what"]),
                  "  %s: %s" % (labels["checked"], finding["checked"])]
        if finding["status"] != "ok":
            lines.append("  %s: %s" % (labels["fix"], finding["fix"]))
            for command in finding["commands"]:
                lines.extend(("  PowerShell: %s" % command["powershell"], "  bash: %s" % command["bash"]))
    if shown.get("sdk") is not None:
        lines += ["", ("[SDK] 委譲した診断: %s" if lang == "ja" else "[SDK] delegated doctor: %s") % shown["sdk"]["status"]]
    lines += ["", ("[SETUP] 環境確認: %s" if lang == "ja" else "[SETUP] environment probe: %s") %
              shown["setup_environment"]["status"]]
    again = _render_command(_argv(sys.executable, "-m", "fullseye", "doctor"))
    lines += ["", labels["again"], "  PowerShell: %s" % again["powershell"], "  bash: %s" % again["bash"]]
    return "\n".join(lines) + "\n"


def _fix_plan(report: dict[str, Any]) -> list[dict[str, Any]]:
    """現在は壊れた QT_PLUGIN_PATH だけを可逆に消せる。 / List only reversible fixes."""
    return [f for f in report["findings"] if f["id"] == "native_dll" and f["fixable"]]


def _powershell_executable() -> Path:
    """既定位置、次に PATH から Windows PowerShell を探す。 / Find Windows PowerShell at its default path, then PATH."""
    default = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
    if default.is_file():
        return default
    found = shutil.which("powershell.exe") or shutil.which("powershell")
    if found:
        return Path(found)
    raise OSError(
        "PowerShell が見つかりません / Windows PowerShell was not found. "
        "確認した場所 / Checked: %s and PATH. "
        "ユーザー環境変数を安全に変更できません / Cannot safely change the per-user setting. "
        "対処 / What to do: Enable Windows PowerShell or add powershell.exe to PATH, then rerun "
        "`fullseye doctor --fix`; otherwise remove only the reported stale QT_PLUGIN_PATH entries manually."
        % default
    )


def _read_user_qt_plugin_path(powershell: Path | str) -> str:
    """利用者単位の QT_PLUGIN_PATH を読むだけで変更しない。 / Read, never change, the per-user QT_PLUGIN_PATH."""
    result = subprocess.run(
        [str(powershell), "-NoProfile", "-Command",
         "[Console]::OutputEncoding = [Text.Encoding]::UTF8; "
         "[Environment]::GetEnvironmentVariable('QT_PLUGIN_PATH', 'User')"],
        check=True, capture_output=True, text=True, encoding="utf-8", timeout=20,
    )
    return result.stdout.rstrip("\r\n")


def _write_user_qt_plugin_path(powershell: Path | str, value: str) -> None:
    """利用者単位の値を一度だけ書く。 / Write the per-user value exactly once."""
    child_env = os.environ.copy()
    child_env["FULLSEYE_DOCTOR_QT_PLUGIN_PATH"] = value
    child_env["FULLSEYE_DOCTOR_QT_PLUGIN_PATH_DELETE"] = "1" if not value else "0"
    subprocess.run(
        [str(powershell), "-NoProfile", "-Command",
         "$next = $env:FULLSEYE_DOCTOR_QT_PLUGIN_PATH; "
         "if ($env:FULLSEYE_DOCTOR_QT_PLUGIN_PATH_DELETE -eq '1') { $next = $null }; "
         "[Environment]::SetEnvironmentVariable('QT_PLUGIN_PATH', $next, 'User')"],
        check=True, capture_output=True, text=True, timeout=20, env=child_env,
    )


def _apply_fixes(plan: Iterable[dict[str, Any]]) -> list[str]:
    """確認済みの古い Qt 項目だけを直す。 / Repair only confirmed stale Qt entries.

    The process environment is changed only after the per-user write succeeds.
    / プロセス環境は、利用者単位の書込み成功後だけ変更する。
    """
    changed: list[str] = []
    for finding in plan:
        if finding["id"] == "native_dll":
            stale = list(finding.get("stale_qt_plugin_paths", ()))
            if not stale:
                continue
            powershell = _powershell_executable()
            persistent = _read_user_qt_plugin_path(powershell)
            persistent_stale = [entry for entry in _stale_qt_plugin_entries(persistent)
                                if os.path.normcase(entry) in {os.path.normcase(item) for item in stale}]
            updated_persistent = _remove_qt_plugin_entries(persistent, persistent_stale)
            if persistent_stale:
                _write_user_qt_plugin_path(powershell, updated_persistent)
            process = os.environ.get("QT_PLUGIN_PATH", "")
            updated_process = _remove_qt_plugin_entries(process, stale)
            if updated_process:
                os.environ["QT_PLUGIN_PATH"] = updated_process
            else:
                os.environ.pop("QT_PLUGIN_PATH", None)
            changed.append(
                "removed stale QT_PLUGIN_PATH entries %s; preserved entries %s"
                % ("; ".join(stale), updated_persistent or "none")
            )
    return changed


def _show_windows_message_box(text: str) -> bool:
    """コンソールなしでは Windows のダイアログで報告する。 / Show a report through a Windows dialog without a console."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        return bool(ctypes.windll.user32.MessageBoxW(0, text, "Fullseye doctor", 0x10))
    except Exception:  # noqa: BLE001 - logging below is the last-resort report channel
        return False


def _write_consoleless_report(text: str) -> str:
    """最後の手段として UTF-8 ログを返す。 / Return a UTF-8 log path as the final fallback."""
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".log", prefix="fullseye-doctor-",
                                     dir=tempfile.gettempdir(), delete=False) as log:
        log.write(text)
        return log.name


def main(argv: Optional[Sequence[str]] = None, *, collect_fn: Callable[[], dict[str, Any]] = collect,
         input_fn: Callable[[str], str] = input, is_tty: Optional[bool] = None,
         apply_fn: Callable[[Iterable[dict[str, Any]]], list[str]] = _apply_fixes, out=None) -> int | str:
    """CLI entry: ``--json`` for tools and conservative ``--fix`` for terminals. / CLI with fail-closed fixing."""
    default_lang = _detect_lang()
    description = ("システムを変更せずに Fullseye の起動問題を診断します。" if default_lang == "ja"
                   else "Diagnose Fullseye startup problems without changing the system.")
    ap = argparse.ArgumentParser(prog="fullseye doctor", description=description)
    ap.add_argument("--lang", choices=["ja", "en"], default=None, help="ja / en (default: from the locale)")
    ap.add_argument("--json", action="store_true", help="print machine-readable diagnostics")
    ap.add_argument("--fix", action="store_true", help="show and confirm safe, reversible repairs")
    ap.add_argument("--yes", action="store_true", help="confirm --fix (ignored without a terminal)")
    args = ap.parse_args(list(argv) if argv is not None else None)
    consoleless = out is None and sys.stdout is None
    out = out if out is not None else (io.StringIO() if consoleless else sys.stdout)

    def finish(status: int) -> int | str:
        if not consoleless:
            return status
        text = out.getvalue()
        return status if _show_windows_message_box(text) else _write_consoleless_report(text)

    try:
        out.reconfigure(errors="replace")
    except Exception:  # noqa: BLE001 - StringIO and redirected streams may not support reconfigure
        pass
    lang = _detect_lang(args.lang)
    report = collect_fn()
    if args.json:
        print(json.dumps(_present_report(report, lang), ensure_ascii=False, indent=2, sort_keys=True), file=out)
    else:
        print(format_report(report, lang), end="", file=out)
    if not args.fix:
        return finish(1 if _has_failures(report) else 0)
    if is_tty is None:
        try:
            from fullseye.setup_cmd import _stdin_is_terminal
            is_tty = _stdin_is_terminal()
        except Exception:  # noqa: BLE001 - a failed terminal probe must never permit a fix
            is_tty = False
    plan = _fix_plan(report)
    if not plan:
        print("安全な自動修復はありません。上の命令を使ってください。" if lang == "ja"
              else "No safe automatic repair is available; use the commands above.", file=out)
        return finish(1 if _has_failures(report) else 0)
    stale = [entry for finding in plan for entry in finding.get("stale_qt_plugin_paths", ())]
    stale_text = "; ".join(stale)
    print("予定した変更: 次の確認済みで存在しない QT_PLUGIN_PATH 項目だけを、プロセスと利用者の値から削除します: %s"
          % stale_text if lang == "ja" else
          "Planned change: remove only these confirmed missing QT_PLUGIN_PATH entries from the process and per-user value: %s"
          % stale_text, file=out)
    if not is_tty:
        print("端末を検出できなかったため、--fix は変更しませんでした。端末で実行して確認してください。" if lang == "ja"
              else "No terminal detected: --fix made no changes. Run in a terminal and confirm.", file=out)
        return finish(1)
    prompt = "この変更を適用しますか? [y/N] " if lang == "ja" else "Apply this change? [y/N] "
    confirmed = args.yes or input_fn(prompt).strip().lower() in {"y", "yes"}
    if not confirmed:
        print("変更しませんでした。" if lang == "ja" else "No changes made.", file=out)
        return finish(1)
    try:
        messages = apply_fn(plan)
    except (OSError, subprocess.SubprocessError) as exc:
        prefix = "変更を完了できませんでした" if lang == "ja" else "No change completed"
        print("%s: %s: %s" % (prefix, type(exc).__name__, exc), file=out)
        return finish(1)
    for message in messages:
        print(("変更しました: %s" if lang == "ja" else "Changed: %s") % message, file=out)
    return finish(0)
