# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Fullseye Studio のスタートメニュー / デスクトップ / アプリケーションメニュー登録。

``fullseye-studio --install-shortcuts [--desktop]`` / ``--remove-shortcuts`` の実体。標準ライブラリだけで動く
(pywin32 不可)。

* Windows: ``%APPDATA%/Microsoft/Windows/Start Menu/Programs/Fullseye/Fullseye Studio.lnk``。起動先は
  **その環境の pythonw.exe** + ``-m studio``(黒いコンソール窓が出ない)。venv の中で実行すれば venv の
  pythonw.exe を指す。.lnk は PowerShell の WScript.Shell COM で作る(引数は環境変数で渡し、引用符・日本語の
  ユーザ名で壊れないようにする)。アイコンは ``%LOCALAPPDATA%/Fullseye/fullseye.ico`` に複製してから指す
  (site-packages の中を指すと pip の更新・削除で切れる)。
* Linux: ``~/.local/share/applications/fullseye-studio.desktop`` と png アイコン。
* macOS: 対応しない(理由を 1 行で言って終了コード 0)。

冪等: 2 回実行しても同じ結果。失敗は原因が分かる文で ``ShortcutError`` にして返す。
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

APP_NAME = "Fullseye Studio"
FOLDER_NAME = "Fullseye"
APP_ID = "Fullseye.Studio"          # studio.py の SetCurrentProcessExplicitAppUserModelID と同じ綴り
_PKG_DIR = Path(__file__).resolve().parent
_ROOT = _PKG_DIR.parent


class ShortcutError(RuntimeError):
    """登録・削除に失敗した(原因を文にして持つ)。"""


# --------------------------------------------------------------------------- 場所の解決
def _platform(platform: Optional[str] = None) -> str:
    p = platform or sys.platform
    if p.startswith("win"):
        return "win"
    if p.startswith("linux"):
        return "linux"
    if p == "darwin":
        return "mac"
    return "other"


def icon_source(kind: str = "ico") -> Path:
    """同梱アイコンの場所。wheel では studio_assets/、checkout では assets/ にもある。"""
    name = "fullseye.ico" if kind == "ico" else "fullseye_256.png"
    for cand in (_ROOT / "studio_assets" / name, _ROOT / "assets" / name):
        if cand.is_file():
            return cand
    raise ShortcutError("icon file %s not found next to the fullseye package (looked in studio_assets/ and assets/); "
                        "reinstall fullseye (pip install --force-reinstall fullseye)" % name)


def windows_dirs(env: Optional[Dict[str, str]] = None) -> Dict[str, Path]:
    """Start Menu / Desktop / icon の既定の場所(環境変数から。テストは env を差し替える)。"""
    e = os.environ if env is None else env
    appdata = e.get("APPDATA")
    local = e.get("LOCALAPPDATA")
    if not appdata or not local:
        raise ShortcutError("APPDATA / LOCALAPPDATA is not set; cannot locate the Start Menu")
    prof = e.get("USERPROFILE") or str(Path.home())
    return {"start_menu": Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / FOLDER_NAME,
            "desktop": Path(prof) / "Desktop",
            "icon_dir": Path(local) / "Fullseye" / "setup"}


def pythonw_path(python: Optional[str] = None) -> Path:
    """この環境の pythonw.exe(コンソール窓なしの python)。venv 内で動いていれば venv のもの。"""
    exe = Path(python or sys.executable)
    cand = exe.with_name("pythonw.exe")
    if cand.is_file():
        return cand
    raise ShortcutError("pythonw.exe not found next to %s (needed to start Studio without a console window). "
                        "Reinstall Python with the standard installer, or run from a normal Python/venv." % exe)


def gui_available() -> bool:
    """Studio の GUI 部品(PySide6)が見えるか(ショートカットが何も起きない物にならないよう警告に使う)。"""
    return importlib.util.find_spec("PySide6") is not None


# --------------------------------------------------------------------------- Windows(.lnk)
_PS_WRITE = """
$ErrorActionPreference = 'Stop'
$sh = New-Object -ComObject WScript.Shell
$lnk = $sh.CreateShortcut($env:FS_LNK)
$lnk.TargetPath = $env:FS_TARGET
$lnk.Arguments = $env:FS_ARGS
$lnk.WorkingDirectory = $env:FS_WORKDIR
$lnk.IconLocation = $env:FS_ICON + ',0'
$lnk.Description = $env:FS_DESC
$lnk.WindowStyle = 1
$lnk.Save()
"""

_PS_READ = """
$ErrorActionPreference = 'Stop'
$sh = New-Object -ComObject WScript.Shell
$l = $sh.CreateShortcut($env:FS_LNK)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
'Target=' + $l.TargetPath
'Arguments=' + $l.Arguments
'Icon=' + $l.IconLocation
'WorkingDir=' + $l.WorkingDirectory
"""


def _powershell(script: str, extra_env: Dict[str, str]) -> str:
    exe = shutil.which("powershell") or shutil.which("pwsh")
    if not exe:
        raise ShortcutError("powershell.exe not found on PATH; it is needed to create a .lnk file")
    env = dict(os.environ)
    env.update(extra_env)
    try:
        r = subprocess.run([exe, "-NoProfile", "-NonInteractive", "-Command", script], env=env,
                           capture_output=True, text=True, encoding="utf-8", timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        raise ShortcutError("could not run PowerShell to write the shortcut: %s" % e) from e
    if r.returncode != 0:
        raise ShortcutError("PowerShell failed to write the shortcut (exit %d): %s"
                            % (r.returncode, (r.stderr or r.stdout).strip()[:300]))
    return r.stdout


def write_lnk(lnk: Path, target: Path, arguments: str, icon: Path, workdir: Path,
              description: str = "Fullseye Studio - visual pipeline workbench") -> None:
    lnk.parent.mkdir(parents=True, exist_ok=True)
    _powershell(_PS_WRITE, {"FS_LNK": str(lnk), "FS_TARGET": str(target), "FS_ARGS": arguments,
                            "FS_WORKDIR": str(workdir), "FS_ICON": str(icon), "FS_DESC": description})
    if not lnk.is_file():
        raise ShortcutError("PowerShell reported success but %s was not created" % lnk)


def read_lnk(lnk: Path) -> Dict[str, str]:
    """.lnk を読み戻して Target / Arguments / Icon / WorkingDir を返す(検証用)。"""
    out = _powershell(_PS_READ, {"FS_LNK": str(lnk)})
    res: Dict[str, str] = {}
    for line in out.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            res[k.strip()] = v.strip()
    return res


# --------------------------------------------------------------------------- 台帳(何を作ったかの記録)
# アンインストールは「推測で消さない」: 登録時に作ったものをこの JSON に書き、消すときはここに載っている物だけを
# 消す(ユーザーが後から置いた物には触らない)。置き場は利用者のデータ領域
# (Windows: %LOCALAPPDATA%/Fullseye/setup/、Linux: ~/.local/share/fullseye/)。環境変数 FULLSEYE_LEDGER で上書き。
# kind: file / dir_if_empty / regkey(HKCU の下位キー)/ claude_skill(~/.claude/skills/fullseye-ops)
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Fullseye"
LEDGER_KINDS = ("file", "dir_if_empty", "regkey", "claude_skill")


def ledger_path() -> Path:
    env = os.environ.get("FULLSEYE_LEDGER")
    if env:
        return Path(env)
    if _platform() == "win" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "Fullseye" / "setup" / "install_ledger.json"
    return _xdg_data() / "fullseye" / "install_ledger.json"


def ledger_load(path: Optional[Path] = None) -> Optional[List[Dict[str, str]]]:
    """台帳の項目一覧。台帳が無ければ None(「古い状態」と区別する)。壊れていれば ShortcutError。"""
    p = path or ledger_path()
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        ents = data["entries"]
        if not isinstance(ents, list):
            raise ValueError("entries is not a list")
        return [e for e in ents if isinstance(e, dict) and e.get("kind") in LEDGER_KINDS and e.get("path")]
    except (OSError, ValueError, KeyError) as e:
        raise ShortcutError("install ledger %s is unreadable (%s); delete it by hand if you want to start over" % (p, e)) from e


def _ledger_save(entries: List[Dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps({"version": 1, "entries": entries}, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def ledger_record(kind: str, target: object, path: Optional[Path] = None) -> None:
    """作った物を台帳に足す(同じ物は重ねない = 冪等)。"""
    assert kind in LEDGER_KINDS, kind
    p = path or ledger_path()
    ents = ledger_load(p) or []
    t = str(target)
    if not any(e["kind"] == kind and e["path"] == t for e in ents):
        ents.append({"kind": kind, "path": t, "created": time.strftime("%Y-%m-%dT%H:%M:%S")})
    _ledger_save(ents, p)


def ledger_forget(kind: str, target: object, path: Optional[Path] = None) -> None:
    p = path or ledger_path()
    ents = ledger_load(p)
    if ents is None:
        return
    t = str(target)
    _ledger_save([e for e in ents if not (e["kind"] == kind and e["path"] == t)], p)


# --------------------------------------------------------------------------- 「アプリと機能」(HKCU の Uninstall キー)
def uninstall_string() -> str:
    """アプリと機能の「アンインストール」が走らせる文字列: fullseye setup --uninstall(終了前に Enter を待つ)。"""
    exe = Path(sys.executable).with_name("fullseye.exe")
    if exe.is_file():
        return '"%s" setup --uninstall --pause' % exe
    return '"%s" -m fullseye setup --uninstall --pause' % sys.executable


def register_uninstall_entry(icon: Path, key: Optional[str] = None) -> str:
    """HKCU に Uninstall キーを作る(管理者権限は要らない)。作ったキーの下位パスを返す。"""
    import winreg
    key = key or UNINSTALL_KEY
    try:
        import fullseye
        ver = fullseye.version()
    except Exception:       # noqa: BLE001
        ver = ""
    try:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "DisplayName", 0, winreg.REG_SZ, "Fullseye (Python package)")
            winreg.SetValueEx(k, "DisplayVersion", 0, winreg.REG_SZ, ver)
            winreg.SetValueEx(k, "Publisher", 0, winreg.REG_SZ, "Kazufumi Furuse")
            winreg.SetValueEx(k, "DisplayIcon", 0, winreg.REG_SZ, str(icon))
            winreg.SetValueEx(k, "UninstallString", 0, winreg.REG_SZ, uninstall_string())
            winreg.SetValueEx(k, "NoModify", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(k, "NoRepair", 0, winreg.REG_DWORD, 1)
    except OSError as e:
        raise ShortcutError("could not write the 'Apps & features' entry HKCU\\%s: %s" % (key, e)) from e
    return key


def unregister_uninstall_entry(key: str) -> bool:
    """キーを消す(無ければ False)。他のキーを巻き込まないよう Uninstall 配下の Fullseye 系だけ許す。"""
    import winreg
    low = key.lower().replace("/", "\\")
    if not (low.startswith("software\\microsoft\\windows\\currentversion\\uninstall\\fullseye")
            or low.startswith("software\\fullseyetest\\")):
        raise ShortcutError("refusing to delete registry key outside the Fullseye uninstall entry: %s" % key)
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key)
        return True
    except FileNotFoundError:
        return False
    except OSError as e:
        raise ShortcutError("could not delete registry key HKCU\\%s: %s" % (key, e)) from e


def regkey_exists(key: str) -> bool:
    import winreg
    try:
        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CURRENT_USER, key))
        return True
    except OSError:
        return False


# --------------------------------------------------------------------------- 本体
def _xdg_data() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")


def _linux_dirs(dirs: Optional[Dict[str, Path]]) -> Dict[str, Path]:
    d = {"apps": _xdg_data() / "applications",
         "icon_dir": _xdg_data() / "icons" / "hicolor" / "256x256" / "apps",
         "desktop": Path.home() / "Desktop"}
    d.update(dirs or {})
    return d


def install(desktop: bool = False, *, python: Optional[str] = None, platform: Optional[str] = None,
            dirs: Optional[Dict[str, Path]] = None, ledger: Optional[Path] = None,
            reg_key: Optional[str] = None) -> List[Path]:
    """登録して、作った(上書きした)ファイルの一覧を返す。mac / 非対応は空リスト。"""
    plat = _platform(platform)
    if plat == "win":
        d = dict(windows_dirs())
        d.update(dirs or {})
        icon_dst = d["icon_dir"] / "fullseye.ico"
        d["icon_dir"].mkdir(parents=True, exist_ok=True)
        shutil.copyfile(icon_source("ico"), icon_dst)
        target = pythonw_path(python)
        made = []
        places = [d["start_menu"]] + ([d["desktop"]] if desktop else [])
        for folder in places:
            lnk = folder / (APP_NAME + ".lnk")
            write_lnk(lnk, target, "-m studio", icon_dst, Path.home())
            made.append(lnk)
            ledger_record("file", lnk, ledger)
        ledger_record("file", icon_dst, ledger)
        for folder in (d["start_menu"], d["icon_dir"]):
            ledger_record("dir_if_empty", folder, ledger)
        ledger_record("regkey", register_uninstall_entry(icon_dst, reg_key), ledger)     # アプリと機能
        return made
    if plat == "linux":
        d = _linux_dirs(dirs)
        d["icon_dir"].mkdir(parents=True, exist_ok=True)
        icon_dst = d["icon_dir"] / "fullseye-studio.png"
        shutil.copyfile(icon_source("png"), icon_dst)
        text = linux_desktop_text(python or sys.executable, icon_dst)
        made = []
        places = [d["apps"]] + ([d["desktop"]] if desktop and d["desktop"].is_dir() else [])
        for folder in places:
            folder.mkdir(parents=True, exist_ok=True)
            f = folder / "fullseye-studio.desktop"
            f.write_text(text, encoding="utf-8")
            try:
                f.chmod(0o755)
            except OSError:
                pass
            made.append(f)
            ledger_record("file", f, ledger)
        ledger_record("file", icon_dst, ledger)
        return made
    return []


def linux_desktop_text(python: str, icon: Path) -> str:
    q = '"%s"' % python if " " in python else python
    return ("[Desktop Entry]\nType=Application\nVersion=1.0\nName=%s\nGenericName=Image Pipeline Workbench\n"
            "Comment=Visual image-processing pipeline workbench (HDevelop-style)\nExec=%s -m studio\nIcon=%s\n"
            "Terminal=false\nCategories=Graphics;Science;Education;\nKeywords=image;vision;pipeline;fullseye;\n"
            "StartupNotify=true\n" % (APP_NAME, q, icon))


def ledger_gc(path: Optional[Path] = None) -> None:
    """もう存在しない物の項目を台帳から落とし、項目が無くなったら台帳ファイルとその空フォルダも畳む。"""
    p = path or ledger_path()
    ents = ledger_load(p)
    if ents is None:
        return
    keep = []
    for e in ents:
        if e["kind"] == "regkey":
            alive = regkey_exists(e["path"])
        else:
            alive = Path(e["path"]).exists()
        if alive:
            keep.append(e)
    if all(e["kind"] == "dir_if_empty" for e in keep):       # 空フォルダだけが残る = 実体は全部消えた
        keep = []
    if keep:
        _ledger_save(keep, p)
        return
    try:
        p.unlink()
        p.parent.rmdir()
    except OSError:
        pass


def _rmdir_quiet(folder: Path) -> None:
    try:
        folder.rmdir()
    except OSError:
        pass


def remove(*, platform: Optional[str] = None, dirs: Optional[Dict[str, Path]] = None,
           ledger: Optional[Path] = None) -> List[Path]:
    """登録を消して、消したファイルの一覧を返す(無ければ空。何度でも呼べる)。"""
    plat = _platform(platform)
    gone: List[Path] = []
    if plat == "win":
        d = dict(windows_dirs())
        d.update(dirs or {})
        known = (d["start_menu"] / (APP_NAME + ".lnk"), d["desktop"] / (APP_NAME + ".lnk"), d["icon_dir"] / "fullseye.ico")
    elif plat == "linux":
        d = _linux_dirs(dirs)
        known = (d["apps"] / "fullseye-studio.desktop", d["desktop"] / "fullseye-studio.desktop",
                 d["icon_dir"] / "fullseye-studio.png")
    else:
        return gone
    for p in known:
        if p.is_file():
            p.unlink()
            gone.append(p)
        ledger_forget("file", p, ledger)
    if plat == "win":
        for e in list(ledger_load(ledger) or []):            # アプリと機能のキー(台帳に載っている物だけ)
            if e["kind"] == "regkey":
                unregister_uninstall_entry(e["path"])
                ledger_forget("regkey", e["path"], ledger)
    ledger_gc(ledger)
    if plat == "win":
        for folder in (d["start_menu"], d["icon_dir"]):      # 空になったときだけ畳む(他の物は消さない)
            _rmdir_quiet(folder)
    return gone


def run_cli(install_mode: bool, desktop: bool = False, *, out=None) -> int:
    """fullseye-studio --install-shortcuts / --remove-shortcuts から呼ぶ。終了コードを返す。"""
    out = out or sys.stdout
    plat = _platform()
    if plat in ("mac", "other"):
        print("fullseye-studio: menu shortcuts are only supported on Windows and Linux; "
              "on this platform start Studio with `fullseye-studio`.", file=out)
        return 0
    try:
        if install_mode:
            if not gui_available():
                print('warning: PySide6 is not installed, so the shortcut will open nothing yet. '
                      'Run: %s -m pip install "PySide6>=6.5"' % sys.executable, file=out)
            made = install(desktop=desktop)
            for p in made:
                print("registered: %s" % p, file=out)
            print("done. Start menu: search for '%s'." % APP_NAME if plat == "win"
                  else "done. Look for '%s' in your application menu." % APP_NAME, file=out)
        else:
            gone = remove()
            for p in gone:
                print("removed: %s" % p, file=out)
            if not gone:
                print("nothing to remove (no Fullseye Studio shortcut was registered).", file=out)
    except ShortcutError as e:
        print("fullseye-studio: %s" % e, file=sys.stderr)
        return 1
    return 0
