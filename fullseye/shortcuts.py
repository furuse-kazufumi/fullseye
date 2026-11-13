# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Fullseye Studio のスタートメニュー / デスクトップ / アプリケーションメニュー登録。

``fullseye-studio --install-shortcuts [--desktop]`` / ``--remove-shortcuts`` の実体。標準ライブラリだけで動く
(pywin32 不可)。

* Windows: ``%APPDATA%/Microsoft/Windows/Start Menu/Programs/Fullseye/Fullseye Studio.lnk``。起動先は
  **その環境の pythonw.exe** + ``-P -m studio``(黒いコンソール窓が出ない。``-P`` は作業フォルダ・ホームに置かれた
  別の studio.py を先に読まないため)。venv の中で実行すれば venv の
  pythonw.exe を指す。.lnk は PowerShell の WScript.Shell COM で作る(引数は環境変数で渡し、引用符・日本語の
  ユーザ名で壊れないようにする)。アイコンは ``%LOCALAPPDATA%/Fullseye/fullseye.ico`` に複製してから指す
  (site-packages の中を指すと pip の更新・削除で切れる)。
* Linux: ``~/.local/share/applications/fullseye-studio.desktop`` と png アイコン。
* macOS: 対応しない(理由を 1 行で言って終了コード 0)。

冪等: 2 回実行しても同じ結果。失敗は原因が分かる文で ``ShortcutError`` にして返す。
"""
from __future__ import annotations

import ctypes
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

APP_NAME = "Fullseye Studio"
FOLDER_NAME = "Fullseye"
STUDIO_ARGS = "-P -m studio"       # -P: sys.path[0](作業フォルダ)を足さない = ホームの studio.py を読まない(Python >= 3.11)
CMD_NAME = "fullseye-uninstall.cmd"   # Python に頼らない後始末スクリプト(「アプリと機能」の UninstallString)
UNINSTALL_FROM_CMD_ENV = "FULLSEYE_UNINSTALL_FROM_CMD"    # この .cmd から呼ばれたとき 1。Python 側は走行中の .cmd を消さない
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


def _known_desktop() -> Optional[Path]:
    """本物のデスクトップ(OneDrive の「既知のフォルダーの移動」で USERPROFILE\\Desktop とは違う場所になる)。

    SHGetKnownFolderPath(FOLDERID_Desktop)。取れなければ None。"""
    if sys.platform != "win32":
        return None
    try:
        from ctypes import wintypes

        class _GUID(ctypes.Structure):
            _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD), ("Data3", wintypes.WORD),
                        ("Data4", ctypes.c_ubyte * 8)]
        guid = _GUID(0xB4BFCC3A, 0xDB2C, 0x424C, (ctypes.c_ubyte * 8)(0xB0, 0x29, 0x7F, 0xE9, 0x9A, 0x87, 0xC6, 0x41))
        out = ctypes.c_void_p()
        fn = ctypes.windll.shell32.SHGetKnownFolderPath
        fn.argtypes = [ctypes.POINTER(_GUID), wintypes.DWORD, wintypes.HANDLE, ctypes.POINTER(ctypes.c_void_p)]
        fn.restype = ctypes.c_long
        if fn(ctypes.byref(guid), 0, None, ctypes.byref(out)) != 0 or not out.value:
            return None
        try:
            path = ctypes.wstring_at(out.value)
        finally:
            ctypes.windll.ole32.CoTaskMemFree(ctypes.c_void_p(out.value))
        p = Path(path)
        return p if p.is_absolute() else None
    except Exception:       # noqa: BLE001 — 取れなければ USERPROFILE\\Desktop に倒す
        return None


def _abs_env(e: Dict[str, str], name: str) -> Optional[str]:
    """環境変数が絶対パスのときだけ返す。相対パス(作業フォルダ依存)は拒否する。"""
    v = e.get(name)
    if not v:
        return None
    if not Path(v).is_absolute():
        raise ShortcutError("%s is a relative path (%r); refusing to build install locations from it" % (name, v))
    return v


def windows_dirs(env: Optional[Dict[str, str]] = None) -> Dict[str, Path]:
    """Start Menu / Desktop / icon の既定の場所。

    ``env`` を渡すとその辞書から(テスト用。デスクトップは USERPROFILE\\Desktop)、省略すると実環境
    (デスクトップは SHGetKnownFolderPath で引く = OneDrive 配下でも本物の場所)。"""
    e = os.environ if env is None else env
    appdata = _abs_env(e, "APPDATA")
    local = _abs_env(e, "LOCALAPPDATA")
    if not appdata or not local:
        raise ShortcutError("APPDATA / LOCALAPPDATA is not set; cannot locate the Start Menu")
    desktop = _known_desktop() if env is None else None
    if desktop is None:
        prof = e.get("USERPROFILE") or str(Path.home())
        desktop = Path(prof) / "Desktop"
    return {"start_menu": Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / FOLDER_NAME,
            "desktop": desktop,
            "icon_dir": Path(local) / "Fullseye" / "setup"}


def launch_workdir() -> Path:
    """Studio を起動するときの作業フォルダ(利用者のホームに置かれたファイルを拾わないよう setup フォルダ)。"""
    try:
        if _platform() == "win":
            d = windows_dirs()["icon_dir"]
            d.mkdir(parents=True, exist_ok=True)
            return d
    except (ShortcutError, OSError):
        pass
    return Path.home()


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
# ★.lnk は IShellLinkW(Unicode の COM)を ctypes で直接呼んで読み書きする。
#   以前は PowerShell の WScript.Shell(``$lnk.TargetPath = ...``)だったが、WSH の ShortcutLink は文字列を**システムの ANSI
#   コードページ**で持つので、そのコードページに無い文字(英語の Windows の日本語のユーザー名、日本語の Windows のタイ語・ヘブライ語
#   など)が ``?`` に化けて ``Unable to save shortcut`` になった(2026-11-13、CI の windows-latest で判明。環境変数で渡した文字は
#   PowerShell まで無傷で届いていて、壊すのは WSH の COM 層)。IShellLinkW + IPersistFile は全部 Unicode で、PowerShell も
#   Add-Type も要らない(Constrained Language Mode でも動く)。COM が使えない環境のためだけに、従来の PowerShell 経路を残す。
class _GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_ulong), ("Data2", ctypes.c_ushort), ("Data3", ctypes.c_ushort),
                ("Data4", ctypes.c_ubyte * 8)]


_CLSID_SHELLLINK = "{00021401-0000-0000-C000-000000000046}"
_IID_ISHELLLINKW = "{000214F9-0000-0000-C000-000000000046}"
_IID_IPERSISTFILE = "{0000010B-0000-0000-C000-000000000046}"


def _guid(text: str) -> "_GUID":
    g = _GUID()
    ctypes.OleDLL("ole32").CLSIDFromString(text, ctypes.byref(g))
    return g


def _vt(obj: "ctypes.c_void_p", index: int, *argtypes, restype=None):
    """COM オブジェクトの仮想関数表の ``index`` 番目を呼び出し可能にする(restype 省略は HRESULT。失敗は OSError)。"""
    vtbl = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
    proto = ctypes.WINFUNCTYPE(restype or ctypes.HRESULT, ctypes.c_void_p, *argtypes)
    return proto(vtbl[index])


class _ComLink:
    """IShellLinkW + IPersistFile の最小の包み(with で使う)。"""

    def __enter__(self) -> "_ComLink":
        if sys.platform != "win32":
            raise OSError("IShellLink is Windows-only")
        ole32 = ctypes.OleDLL("ole32")
        self.link = ctypes.c_void_p()
        self.persist = ctypes.c_void_p()
        self._co_initialized = False
        try:
            # COINIT_APARTMENTTHREADED。S_OK / S_FALSE(既に同じ方式で初期化済み)は成功で、どちらも CoUninitialize と対にする。
            # RPC_E_CHANGED_MODE(呼び出し元が別の方式で初期化済み)は OSError: そのまま使い、CoUninitialize はしない。
            ole32.CoInitializeEx(None, 2)
            self._co_initialized = True
        except OSError:
            pass
        try:
            iid = _guid(_IID_ISHELLLINKW)
            clsid = _guid(_CLSID_SHELLLINK)
            ole32.CoCreateInstance(ctypes.byref(clsid), None, 1, ctypes.byref(iid), ctypes.byref(self.link))   # INPROC_SERVER
            piid = _guid(_IID_IPERSISTFILE)
            _vt(self.link, 0, ctypes.POINTER(_GUID), ctypes.POINTER(ctypes.c_void_p))(self.link, ctypes.byref(piid),
                                                                                      ctypes.byref(self.persist))
        except BaseException:
            self._release()                 # 途中で失敗しても、作った ShellLink の参照と COM の初期化を戻す
            raise
        return self

    def _release(self) -> None:
        for p in (self.persist, self.link):
            if p is not None and p.value:
                _vt(p, 2, restype=ctypes.c_ulong)(p)    # Release
                p.value = None
        if getattr(self, "_co_initialized", False):
            ctypes.WinDLL("ole32").CoUninitialize()
            self._co_initialized = False

    def __exit__(self, *exc) -> None:
        self._release()

    # IShellLinkW(仮想関数表の番号): 3 GetPath 8 GetWorkingDirectory 10 GetArguments 16 GetIconLocation
    #                              7 SetDescription 9 SetWorkingDirectory 11 SetArguments 15 SetShowCmd 17 SetIconLocation 20 SetPath
    def set(self, target: str, arguments: str, workdir: str, icon: str, description: str) -> None:
        w = ctypes.c_wchar_p
        _vt(self.link, 20, w)(self.link, target)
        _vt(self.link, 11, w)(self.link, arguments)
        _vt(self.link, 9, w)(self.link, workdir)
        _vt(self.link, 17, w, ctypes.c_int)(self.link, icon, 0)
        _vt(self.link, 7, w)(self.link, description)
        _vt(self.link, 15, ctypes.c_int)(self.link, 1)              # SW_SHOWNORMAL

    def save(self, path: str) -> None:
        _vt(self.persist, 6, ctypes.c_wchar_p, ctypes.c_int)(self.persist, path, 1)     # IPersistFile::Save(path, fRemember)

    def load(self, path: str) -> None:
        _vt(self.persist, 5, ctypes.c_wchar_p, ctypes.c_ulong)(self.persist, path, 0)   # IPersistFile::Load(path, STGM_READ)

    def get(self) -> Dict[str, str]:
        buf = ctypes.create_unicode_buffer(32768)
        out: Dict[str, str] = {}
        _vt(self.link, 3, ctypes.c_wchar_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_ulong)(self.link, buf, 32768, None, 0)
        out["Target"] = buf.value
        _vt(self.link, 10, ctypes.c_wchar_p, ctypes.c_int)(self.link, buf, 32768)
        out["Arguments"] = buf.value
        idx = ctypes.c_int(0)
        _vt(self.link, 16, ctypes.c_wchar_p, ctypes.c_int, ctypes.POINTER(ctypes.c_int))(self.link, buf, 32768, ctypes.byref(idx))
        out["Icon"] = "%s,%d" % (buf.value, idx.value)
        _vt(self.link, 8, ctypes.c_wchar_p, ctypes.c_int)(self.link, buf, 32768)
        out["WorkingDir"] = buf.value
        return out


# 従来の PowerShell(WScript.Shell)経路。COM が使えない環境のための退避(ANSI コードページに無い文字のパスでは壊れる)。
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


def powershell_path(env: Optional[Dict[str, str]] = None) -> Path:
    """Windows PowerShell 5.1 を **絶対パス**で返す(退避の経路だけが使う)。

    ``shutil.which`` は Python 3.11 の Windows で作業フォルダを PATH より先に引く(置かれた powershell.bat が走る)。
    %SystemRoot%\\System32\\WindowsPowerShell\\v1.0\\powershell.exe だけを使い、無ければ明示的なエラーにする。"""
    e = os.environ if env is None else env
    root = e.get("SystemRoot") or e.get("windir")
    if root and Path(root).is_absolute():
        cand = Path(root) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
        if cand.is_file():
            return cand
    raise ShortcutError("Windows PowerShell not found at %%SystemRoot%%\\System32\\WindowsPowerShell\\v1.0\\powershell.exe "
                        "(SystemRoot=%r); it is needed to create a .lnk file" % root)


def _powershell(script: str, extra_env: Dict[str, str]) -> str:
    exe = str(powershell_path())
    env = dict(os.environ)
    env.update(extra_env)
    try:
        r = subprocess.run([exe, "-NoProfile", "-NonInteractive", "-Command", script], env=env,
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        raise ShortcutError("could not run PowerShell to write the shortcut: %s" % e) from e
    if r.returncode != 0:
        raise ShortcutError("PowerShell failed to write the shortcut (exit %d): %s"
                            % (r.returncode, (r.stderr or r.stdout).strip()[:300]))
    return r.stdout


def _write_lnk_via_powershell(lnk: Path, target: Path, arguments: str, icon: Path, workdir: Path, description: str) -> None:
    _powershell(_PS_WRITE, {"FS_LNK": str(lnk), "FS_TARGET": str(target), "FS_ARGS": arguments,
                            "FS_WORKDIR": str(workdir), "FS_ICON": str(icon), "FS_DESC": description})


def _read_lnk_via_powershell(lnk: Path) -> Dict[str, str]:
    out = _powershell(_PS_READ, {"FS_LNK": str(lnk)})
    res: Dict[str, str] = {}
    for line in out.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            res[k.strip()] = v.strip()
    return res


def write_lnk(lnk: Path, target: Path, arguments: str, icon: Path, workdir: Path,
              description: str = "Fullseye Studio - visual pipeline workbench") -> None:
    lnk.parent.mkdir(parents=True, exist_ok=True)
    try:
        with _ComLink() as c:
            c.set(str(target), arguments, str(workdir), str(icon), description)
            c.save(str(lnk))
    except Exception:       # noqa: BLE001 — COM が使えない環境だけ、従来の経路へ
        _write_lnk_via_powershell(lnk, target, arguments, icon, workdir, description)
    if not lnk.is_file():
        raise ShortcutError("the shortcut was reported as written but %s was not created" % lnk)


def read_lnk(lnk: Path) -> Dict[str, str]:
    """.lnk を読み戻して Target / Arguments / Icon / WorkingDir を返す(検証用)。"""
    try:
        with _ComLink() as c:
            c.load(str(lnk))
            return c.get()
    except Exception:       # noqa: BLE001
        return _read_lnk_via_powershell(lnk)


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
        local = _abs_env(os.environ, "LOCALAPPDATA")
        return Path(local or "") / "Fullseye" / "setup" / "install_ledger.json"
    return _xdg_data() / "fullseye" / "install_ledger.json"


def env_owner() -> str:
    """この Python 環境の目印(sys.prefix)。台帳の項目に書き、別の環境が作った物を消さないために使う。"""
    return os.path.abspath(sys.prefix)


def owner_of_python(python: Optional[str] = None) -> str:
    """登録する物が指す Python の環境の目印。省略(= この環境)なら ``env_owner()``、``python=`` で別の Python を
    指すときは、その venv の根(pyvenv.cfg がある)か、その python.exe のあるフォルダ。"""
    if not python or _same_path(python, sys.executable):
        return env_owner()
    exe = Path(python)
    for cand in (exe.parent.parent, exe.parent):
        if (cand / "pyvenv.cfg").is_file():
            return os.path.abspath(cand)
    return os.path.abspath(exe.parent)


def _same_path(a: str, b: str) -> bool:
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def entry_foreign(e: Dict[str, str]) -> Optional[str]:
    """項目が**別の環境**の物なら、その環境の目印を返す(この環境の物、または不明なら None)。"""
    o = e.get("owner")
    if isinstance(o, str) and o and not _same_path(o, env_owner()):
        return o
    return None


def ledger_load(path: Optional[Path] = None) -> Optional[List[Dict[str, str]]]:
    """台帳の項目一覧。台帳が無ければ None(「古い状態」と区別する)。壊れていれば ShortcutError。"""
    p = path or ledger_path()
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("top level is not an object")
        ents = data.get("entries")
        if not isinstance(ents, list):
            raise ValueError("entries is not a list")
        return [e for e in ents if isinstance(e, dict) and e.get("kind") in LEDGER_KINDS
                and isinstance(e.get("path"), str) and e["path"]]
    except (OSError, ValueError, RecursionError) as e:
        raise ShortcutError("install ledger %s is unreadable (%s); delete it by hand if you want to start over" % (p, e)) from e


def ledger_load_safe(path: Optional[Path] = None) -> Tuple[Optional[List[Dict[str, str]]], Optional[str]]:
    """(項目一覧, 警告)。壊れた台帳は例外にせず (None, 警告文) を返す = 呼び出し側は「台帳なし」に倒せる。"""
    try:
        return ledger_load(path), None
    except ShortcutError as e:
        return None, str(e)


def _ledger_save(entries: List[Dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps({"version": 1, "entries": entries}, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def ledger_record(kind: str, target: object, path: Optional[Path] = None, owner: Optional[str] = None) -> None:
    """作った物を台帳に足す(同じ物は重ねない = 冪等)。持ち主(既定はこの環境の sys.prefix)も書く。"""
    assert kind in LEDGER_KINDS, kind
    p = path or ledger_path()
    ents = ledger_load(p) or []
    t = str(target)
    me = owner or env_owner()
    for e in ents:
        if e["kind"] == kind and e["path"] == t:
            e["owner"] = me                    # 後から登録した環境がその物の持ち主(.lnk はその環境の pythonw を指す)
            break
    else:
        ents.append({"kind": kind, "path": t, "created": time.strftime("%Y-%m-%dT%H:%M:%S"), "owner": me})
    _ledger_save(ents, p)


def ledger_forget(kind: str, target: object, path: Optional[Path] = None) -> None:
    p = path or ledger_path()
    ents, _warn = ledger_load_safe(p)
    if ents is None:
        return
    t = str(target)
    _ledger_save([e for e in ents if not (e["kind"] == kind and e["path"] == t)], p)


# --------------------------------------------------------------------------- 台帳の中身を検証する(許可制)
# 台帳は利用者が書き換えられる JSON(環境変数 FULLSEYE_LEDGER で別のファイルにも差し替えられる)。台帳に書いて
# あるからといって何でも消さない: setup が作る物の**名前**と**置き場**だけを許す。
_FILE_NAMES = frozenset({APP_NAME + ".lnk", "fullseye.ico", CMD_NAME, "fullseye-studio.desktop", "fullseye-studio.png"})


def _norm(p: object) -> str:
    return os.path.normcase(os.path.normpath(str(p)))


def allowed_parents(plat: str, dirs: Optional[Dict[str, Path]] = None) -> Tuple[set, set]:
    """(ファイルを置いてよい親フォルダ, 空なら畳んでよいフォルダ)。"""
    if plat == "win":
        d = dict(windows_dirs())
        d.update(dirs or {})
        prof = os.environ.get("USERPROFILE") or str(Path.home())
        files = {_norm(d["start_menu"]), _norm(d["start_menu"].parent), _norm(d["desktop"]), _norm(d["icon_dir"]),
                 _norm(Path(prof) / "Desktop")}
        return files, {_norm(d["start_menu"]), _norm(d["icon_dir"])}
    if plat == "linux":
        d = _linux_dirs(dirs)
        return {_norm(d["apps"]), _norm(d["desktop"]), _norm(d["icon_dir"])}, set()
    return set(), set()


def check_ledger_item(kind: str, path: str, *, plat: Optional[str] = None, dirs: Optional[Dict[str, Path]] = None,
                      allow_keys: Iterable[str] = ()) -> Optional[str]:
    """台帳の 1 項目を消してよいか。よければ None、だめなら理由の文(消さずに画面へ出す)。"""
    plat = _platform(plat)
    if kind == "regkey":
        k = _key_norm(path)
        if k == _key_norm(UNINSTALL_KEY) or k in {_key_norm(a) for a in allow_keys}:
            return None
        return "registry key %s is not the Fullseye 'Apps & features' entry; left alone" % path
    if kind == "claude_skill":
        from fullseye import rag_setup
        p = Path(path)
        if p.name != rag_setup.SKILL_NAME:
            return "%s is not a %s directory; left alone" % (p, rag_setup.SKILL_NAME)
        try:
            if _norm(p.parent) == _norm(rag_setup.default_target()):
                return None
        except (OSError, RuntimeError):
            pass
        if (p / rag_setup.MARKER_NAME).is_file():
            return None
        return ("%s is not under the default Claude skills folder and has no %s marker (fullseye-rag writes it); "
                "left alone" % (p, rag_setup.MARKER_NAME))
    if kind not in ("file", "dir_if_empty"):
        return "unknown ledger kind %r; left alone" % kind
    p = Path(path)
    if not p.is_absolute():
        return "%s is not an absolute path; left alone" % path
    try:
        files, dirs_ok = allowed_parents(plat, dirs)
    except ShortcutError as e:
        return "cannot resolve the install folders (%s); left alone" % e
    if kind == "file":
        if os.path.normcase(p.name) not in {os.path.normcase(n) for n in _FILE_NAMES}:
            return "%s is not a file name fullseye setup creates; left alone" % p
        if _norm(p.parent) not in files:
            return "%s is outside the folders fullseye setup writes to; left alone" % p
        return None
    if _norm(p) not in dirs_ok:
        return "%s is not a folder fullseye setup created; left alone" % p
    return None


FULLSEYE_DISPLAY_NAME = "Fullseye (Python package)"       # register_uninstall_entry が書く DisplayName
_ICO_MAGIC = b"\x00\x00\x01\x00"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def verify_fullseye_item(kind: str, path: str, *, plat: Optional[str] = None) -> Optional[str]:
    """消す前に、それが**Fullseye の物だと中身で**確かめる(名前と置き場だけで消さない)。確かめられなければ理由の文。

    * ``.lnk``: 指す先の引数が Fullseye Studio の起動(``-m studio``、または install.ps1 の ``studio.py``)。
    * ``.cmd``: 先頭に後始末スクリプトの印がある。``.ico`` / ``.png``: 画像の先頭の印。``.desktop``: Name と ``-m studio``。
    * ``regkey``: DisplayName が Fullseye の物で、UninstallString が後始末(``fullseye-uninstall.cmd`` / ``setup --uninstall``)。
    実在しない物は「消す物が無い」ので None(問題なし)。"""
    plat = _platform(plat)
    if kind == "regkey":
        if plat != "win":
            return None
        import winreg
        try:
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path)
        except OSError:
            return None
        with k:
            try:
                name = str(winreg.QueryValueEx(k, "DisplayName")[0])
                us = str(winreg.QueryValueEx(k, "UninstallString")[0])
            except OSError:
                return "registry key %s has no DisplayName / UninstallString that identify it as Fullseye's; left alone" % path
        if name != FULLSEYE_DISPLAY_NAME or not (CMD_NAME.lower() in us.lower() or "setup --uninstall" in us.lower()):
            return ("registry key %s is not Fullseye's (DisplayName %r, UninstallString %r); left alone" % (path, name, us))
        return None
    if kind != "file":
        return None
    p = Path(path)
    if not p.is_file():
        return None
    low = p.name.lower()
    try:
        if low.endswith(".lnk"):
            if plat != "win":
                return "%s is a .lnk on a non-Windows system; left alone" % p
            args = read_lnk(p).get("Arguments", "").lower()
            if "-m studio" in args or "studio.py" in args:
                return None
            return "%s does not start Fullseye Studio (its arguments are %r); left alone" % (p, args)
        head = p.read_bytes()[:4096]
        if low.endswith(".ico"):
            ok = head[:4] == _ICO_MAGIC
        elif low.endswith(".png"):
            ok = head[:8] == _PNG_MAGIC
        elif low == CMD_NAME.lower():
            ok = b"Fullseye uninstall helper" in head
        elif low.endswith(".desktop"):
            ok = b"Name=" + APP_NAME.encode() in head and b"-m studio" in head
        else:
            return "%s is not a kind of file fullseye setup creates; left alone" % p
    except (OSError, ShortcutError) as e:
        return "cannot verify that %s belongs to Fullseye (%s); left alone" % (p, e)
    return None if ok else "%s does not look like the file fullseye setup created; left alone" % p


def _key_norm(k: str) -> str:
    return k.replace("/", "\\").strip("\\").lower()


# --------------------------------------------------------------------------- 「アプリと機能」(HKCU の Uninstall キー)
def uninstall_string(script: Optional[Path] = None) -> str:
    """アプリと機能の「アンインストール」が走らせる文字列。

    Python に頼らない後始末スクリプト(setup フォルダの fullseye-uninstall.cmd)があればそれ。venv を消した後でも
    項目が消せる。無ければ従来どおり ``fullseye setup --uninstall --pause``。"""
    if script is not None:
        return '"%s"' % script
    exe = Path(sys.executable).with_name("fullseye.exe")
    if exe.is_file():
        return '"%s" setup --uninstall --pause' % exe
    return '"%s" -m fullseye setup --uninstall --pause' % sys.executable


def register_uninstall_entry(icon: Path, key: Optional[str] = None, script: Optional[Path] = None) -> str:
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
            winreg.SetValueEx(k, "UninstallString", 0, winreg.REG_SZ, uninstall_string(script))
            winreg.SetValueEx(k, "NoModify", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(k, "NoRepair", 0, winreg.REG_DWORD, 1)
    except OSError as e:
        raise ShortcutError("could not write the 'Apps & features' entry HKCU\\%s: %s" % (key, e)) from e
    return key


def unregister_uninstall_entry(key: str, allow_keys: Iterable[str] = ()) -> bool:
    """キーを消す(無ければ False)。許すのは Uninstall\\Fullseye(完全一致)と、引数で明示された物だけ。"""
    why = check_ledger_item("regkey", key, allow_keys=allow_keys)
    if why:
        raise ShortcutError("refusing to delete registry key: %s" % why)
    if sys.platform != "win32":
        raise ShortcutError("the registry exists only on Windows; cannot delete registry key %s" % key)
    import winreg
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key)
        return True
    except FileNotFoundError:
        return False
    except OSError as e:
        raise ShortcutError("could not delete registry key HKCU\\%s: %s" % (key, e)) from e


def regkey_exists(key: str) -> bool:
    if sys.platform != "win32":         # Linux / macOS にレジストリは無い(台帳に regkey の行があっても落ちない = 「無い」)
        return False
    import winreg
    try:
        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CURRENT_USER, key))
        return True
    except OSError:
        return False


# --------------------------------------------------------------------------- Python に頼らない後始末スクリプト(.cmd)
_DYNAMIC_CMD_VARS = frozenset({"CD", "DATE", "TIME", "RANDOM", "ERRORLEVEL", "CMDEXTVERSION", "CMDCMDLINE", "HIGHESTNUMANODENUMBER"})


def reject_expandable_percent(path: object) -> None:
    """パスに、cmd が展開してしまう ``%NAME%``(定義済みの環境変数、または %CD% など)があれば拒否する。

    「アプリと機能」は UninstallString を cmd.exe に渡す。そのとき ``%NAME%`` は展開され、別のパスになって起動に失敗する
    (.cmd の中の ``%`` は ``%%`` で逃がしているが、起動の行は逃がせない)。登録の時点で理由を言って止める。"""
    for m in re.finditer(r"%([^%\r\n=]+)%", str(path)):
        name = m.group(1)
        if name.upper() in _DYNAMIC_CMD_VARS or os.environ.get(name) is not None:
            raise ShortcutError("the setup folder path %s contains %%%s%%, which cmd.exe would expand when 'Apps & features' "
                                "runs the uninstaller; choose a LOCALAPPDATA without a %%NAME%% pattern" % (path, name))


def _cmd_val(p: object) -> str:
    """.cmd の ``set "X=..."`` / ``del "..."`` に安全に書ける形にする(% は %% に。引用符・改行は拒否)。"""
    s = str(p)
    if any(c in s for c in '"\r\n\0'):
        raise ShortcutError("path contains a character that cannot be written into the uninstall script: %r" % s)
    return s.replace("%", "%%")


def uninstall_cmd_text(*, python: object, uninstaller: object, lnks: Iterable[object], regkey: str) -> str:
    """setup フォルダに置く fullseye-uninstall.cmd の中身。

    1. python と fullseye/uninstall.py があれば ``python -I uninstall.py --uninstall --pause``(パッケージ本体を import
       しないので、scipy が壊れた環境でも動く)。終わって Uninstall キーが消えていれば、この .cmd 自身と空の setup
       フォルダを消す(Python に走行中の .cmd を消させない)。
    2. 無ければ(venv を消した / 直接 pip uninstall した後)、**固定の名前だけ**を消す: .lnk・アイコン・台帳・
       Uninstall キー・自分自身。"""
    lnks = [Path(str(x)) for x in lnks]
    L = ["@echo off",
         "rem Fullseye uninstall helper, written by `fullseye setup`. Needs neither Python nor the fullseye package.",
         "chcp 65001 >nul",
         "setlocal",
         'set "FS_PY=%s"' % _cmd_val(python),
         'set "FS_UNINST=%s"' % _cmd_val(uninstaller),
         'if not exist "%FS_PY%" goto fallback',
         'if not exist "%FS_UNINST%" goto fallback',
         # python.exe が在っても起動できない(venv の元の Python を消した = pyvenv.cfg の home が無い、rc 103)ことがある。
         # 起動を確かめて、だめなら Python に頼らない後始末へ進む(進まないと「アプリと機能」から永久に消せない)。
         # ★`if errorlevel 1` は「1 以上」の判定で、DLL が無いときの負の終了コード(0xC0000135 = -1073741515)を見逃す。
         #   終了コードが 0 かどうかで分岐する `||` / `&&` を使う。
         '"%FS_PY%" -I -c "0" >nul 2>&1 || goto fallback',
         # Python 側はこの .cmd を消さない(実行中のバッチが消えると cmd が「見つかりません」を出して終了コードも壊れる)。
         # 消すのは、Python が終わった後でこのバッチ自身。
         'set "%s=1"' % UNINSTALL_FROM_CMD_ENV,
         '"%FS_PY%" -I "%FS_UNINST%" --uninstall --pause %*',
         'set "FS_RC=%errorlevel%"',
         # Uninstall キーがまだ在る = 後始末が完了していない(--dry-run・「いいえ」・失敗)ので、この .cmd は残す
         'reg query "HKCU\\%s" >nul 2>&1 && exit /b %%FS_RC%%' % _cmd_val(regkey),
         'pushd "%TEMP%"',
         '(goto) 2>nul & del "%~f0" & rmdir "%~dp0" 2>nul & exit /b %FS_RC%',
         ":fallback",
         'if /i "%~1"=="--dry-run" goto dry',
         "echo.",
         "echo Fullseye: Python or the fullseye package is no longer there. Removing what setup created.",
         'pushd "%TEMP%"']
    for x in lnks:
        L.append('del "%s" 2>nul' % _cmd_val(x))
    for x in lnks:
        if x.parent.name == FOLDER_NAME:
            L.append('rmdir "%s" 2>nul' % _cmd_val(x.parent))
    L += ['del "%~dp0fullseye.ico" 2>nul',
          'del "%~dp0install_ledger.json" 2>nul',
          'reg delete "HKCU\\%s" /f >nul 2>&1' % _cmd_val(regkey),
          "echo Done. (Studio settings, the cache and any Claude Code skill were kept.)",
          'if not defined FS_NOPAUSE pause',
          # 自分自身と setup フォルダ(空なら)を消す。1 行で連ねるのは、バッチ終了後も展開済みの文を走らせるため
          '(goto) 2>nul & del "%~f0" & rmdir "%~dp0" 2>nul',
          ":dry",
          "echo (--dry-run) Python or the fullseye package is gone; this script would remove the Fullseye shortcuts,",
          "echo the Apps and features entry and itself. Nothing was changed.",
          "exit /b 0", ""]
    return "\r\n".join(L)


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
    """登録して、作った(上書きした)ファイルの一覧を返す。mac / 非対応は空リスト。

    作った物は**作った直後に**台帳へ書く(途中で失敗しても、そこまでに作った物はアンインストールで消せる)。"""
    plat = _platform(platform)
    owner = owner_of_python(python)
    if plat == "win":
        d = dict(windows_dirs())
        d.update(dirs or {})
        icon_dst = d["icon_dir"] / "fullseye.ico"
        reject_expandable_percent(d["icon_dir"])
        d["icon_dir"].mkdir(parents=True, exist_ok=True)
        ledger_record("dir_if_empty", d["icon_dir"], ledger, owner)
        shutil.copyfile(icon_source("ico"), icon_dst)
        ledger_record("file", icon_dst, ledger, owner)
        target = pythonw_path(python)
        made = []
        places = [d["start_menu"]] + ([d["desktop"]] if desktop else [])
        for folder in places:
            lnk = folder / (APP_NAME + ".lnk")
            write_lnk(lnk, target, STUDIO_ARGS, icon_dst, d["icon_dir"])
            made.append(lnk)
            ledger_record("file", lnk, ledger, owner)
            if folder == d["start_menu"]:
                ledger_record("dir_if_empty", folder, ledger, owner)
        key = reg_key or UNINSTALL_KEY
        script = d["icon_dir"] / CMD_NAME
        known_lnks = {str(x): x for x in made}                   # 前の登録で作った .lnk(別の場所のデスクトップ等)も消せるように
        for e in (ledger_load(ledger) or []):
            if e["kind"] == "file" and Path(e["path"]).name == APP_NAME + ".lnk" and \
                    check_ledger_item("file", e["path"], plat="win", dirs=dirs) is None:
                known_lnks.setdefault(e["path"], Path(e["path"]))
        script.write_text(uninstall_cmd_text(python=Path(python or sys.executable), uninstaller=_PKG_DIR / "uninstall.py",
                                             lnks=list(known_lnks.values()), regkey=key),
                          encoding="utf-8", newline="")
        ledger_record("file", script, ledger, owner)
        ledger_record("regkey", register_uninstall_entry(icon_dst, key, script), ledger, owner)     # アプリと機能
        return made
    if plat == "linux":
        d = _linux_dirs(dirs)
        d["icon_dir"].mkdir(parents=True, exist_ok=True)
        icon_dst = d["icon_dir"] / "fullseye-studio.png"
        shutil.copyfile(icon_source("png"), icon_dst)
        ledger_record("file", icon_dst, ledger, owner)
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
            ledger_record("file", f, ledger, owner)
        return made
    return []


def _desktop_arg(arg: str) -> str:
    """.desktop の Exec に書く 1 引数(Desktop Entry 仕様: 予約文字があれば二重引用符で囲み、``" ` $ \\`` を
    バックスラッシュで逃がし、文字列としてもう一度バックスラッシュを重ね、``%`` は ``%%``)。"""
    if any(c in arg for c in "\r\n\0"):
        raise ShortcutError("path contains a line break and cannot be written into a .desktop file: %r" % arg)
    reserved = set(" \t\"'\\><~|&;$*?#()`")
    if not any(c in reserved for c in arg):
        return arg.replace("%", "%%")
    inner = "".join("\\" + c if c in '"`$\\' else c for c in arg)
    return ('"%s"' % inner).replace("\\", "\\\\").replace("%", "%%")


def linux_desktop_text(python: str, icon: Path) -> str:
    if any(c in str(icon) for c in "\r\n"):
        raise ShortcutError("icon path contains a line break: %r" % str(icon))
    return ("[Desktop Entry]\nType=Application\nVersion=1.0\nName=%s\nGenericName=Image Pipeline Workbench\n"
            "Comment=Visual image-processing pipeline workbench (HDevelop-style)\nExec=%s %s\nIcon=%s\n"
            "Terminal=false\nCategories=Graphics;Science;Education;\nKeywords=image;vision;pipeline;fullseye;\n"
            "StartupNotify=true\n" % (APP_NAME, _desktop_arg(python), STUDIO_ARGS, icon))


def ledger_gc(path: Optional[Path] = None) -> None:
    """もう存在しない物の項目を台帳から落とし、項目が無くなったら台帳ファイルとその空フォルダも畳む。"""
    p = path or ledger_path()
    ents, _warn = ledger_load_safe(p)
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
    except OSError:
        return
    if p.name == "install_ledger.json" and p.parent.name.lower() == "setup":      # 既定の置き場だけ畳む(任意の親は触らない)
        _rmdir_quiet(p.parent)


def _rmdir_quiet(folder: Path) -> None:
    try:
        folder.rmdir()
    except OSError:
        pass


def _known_default_files(plat: str, d: Dict[str, Path]) -> List[Path]:
    """台帳が無いとき(古い状態)に消してよい既知の場所: 既定の登録先の物だけ(デスクトップは台帳が無ければ触らない)。"""
    if plat == "win":
        return [d["start_menu"] / (APP_NAME + ".lnk"), d["icon_dir"] / "fullseye.ico", d["icon_dir"] / CMD_NAME]
    return [d["apps"] / "fullseye-studio.desktop", d["icon_dir"] / "fullseye-studio.png"]


def remove(*, platform: Optional[str] = None, dirs: Optional[Dict[str, Path]] = None,
           ledger: Optional[Path] = None, allow_keys: Iterable[str] = (),
           removed_keys: Optional[List[str]] = None, skipped: Optional[List[Tuple[str, str]]] = None) -> List[Path]:
    """登録を消して、消したファイルの一覧を返す(無ければ空。何度でも呼べる)。

    台帳があれば**台帳に載り、検証を通り、この環境が作った物だけ**を消す(台帳に無いデスクトップの同名 .lnk には触らない)。
    台帳が無い / 壊れているときは既定の登録先だけ。消した Uninstall キーは ``removed_keys``、消さなかった物とその理由は
    ``skipped`` に足す。"""
    plat = _platform(platform)
    gone: List[Path] = []
    if plat == "win":
        d = dict(windows_dirs())
        d.update(dirs or {})
    elif plat == "linux":
        d = _linux_dirs(dirs)
    else:
        return gone
    skipped = skipped if skipped is not None else []
    removed_keys = removed_keys if removed_keys is not None else []
    ents, _warn = ledger_load_safe(ledger)
    if ents is None:
        todo = [("file", {"path": str(p)}) for p in _known_default_files(plat, d)]
    else:
        todo = [(e["kind"], e) for e in ents if e["kind"] == "file" or (e["kind"] == "regkey" and plat == "win")]
    for kind, e in todo:
        why = check_ledger_item(kind, e["path"], plat=plat, dirs=dirs, allow_keys=allow_keys)
        if why is None and entry_foreign(e):
            why = "%s was created by another Python environment (%s); left alone" % (e["path"], entry_foreign(e))
        if why is None:
            why = verify_fullseye_item(kind, e["path"], plat=plat)
        if why:
            skipped.append((e["path"], why))
            continue
        if kind == "file":
            p = Path(e["path"])
            if p.is_file():
                p.unlink()
                gone.append(p)
            ledger_forget("file", p, ledger)
        else:
            if unregister_uninstall_entry(e["path"], allow_keys):
                removed_keys.append(e["path"])
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
            keys: List[str] = []
            skipped: List[Tuple[str, str]] = []
            gone = remove(removed_keys=keys, skipped=skipped)
            for p in gone:
                print("removed: %s" % p, file=out)
            for k in keys:
                print("removed registry entry: HKCU\\%s" % k, file=out)
            for _p, why in skipped:
                print("kept: %s" % why, file=out)
            if not gone and not keys and not skipped:
                print("nothing to remove (no Fullseye Studio shortcut was registered).", file=out)
    except ShortcutError as e:
        print("fullseye-studio: %s" % e, file=sys.stderr)
        return 1
    return 0
